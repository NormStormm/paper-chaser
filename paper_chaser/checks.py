"""Step 2: plain-code accounting checks on what Claude extracted. No AI in this file.

Each document gets a decision:
  APPROVED  - ready to enter for payment (may carry notes, e.g. "within tolerance")
  HOLD      - a person must look first; every reason is listed in plain language
"""
from __future__ import annotations

import csv
import difflib
import pathlib
import re
from dataclasses import dataclass, field
from datetime import date

PO_TOLERANCE = 0.02             # invoice may be up to 2% over its PO
MATH_TOLERANCE = 0.02           # dollars: rounding slack when re-adding an invoice
MIN_EACH_OCCURRENCE = 1_000_000 # required general-liability limit for on-site contractors
COI_WARNING_DAYS = 30           # warn when a certificate expires within this many days

# Plain-language text for each reason code (shown in the Excel file).
REASONS = {
    "NOT_AN_INVOICE": "Not an invoice (e.g. a statement or letter); nothing to pay",
    "UNREADABLE": "Couldn't read the document: {detail}",
    "INCOMPLETE": "Key details missing: {detail}",
    "UNKNOWN_VENDOR": "Vendor \"{detail}\" isn't in the vendor list",
    "MISSING_PO": "No PO number on the invoice",
    "PO_NOT_FOUND": "PO {detail} doesn't exist",
    "PO_VENDOR_MISMATCH": "PO {detail}",
    "AMOUNT_OVER_PO": "{detail}",
    "MATH_ERROR": "Invoice doesn't add up: {detail}",
    "DUPLICATE": "Duplicate of {detail}",
    "POSSIBLE_DUPLICATE": "Possible duplicate of {detail}",
    "COI_MISSING": "Contractor has no certificate of insurance on file",
    "COI_EXPIRED": "Insurance expired {detail}",
    "COI_COVERAGE_LOW": "Insurance limit {detail}",
    "WITHIN_TOLERANCE": "{detail}",
    "COI_EXPIRING": "Insurance expires {detail}",
}


@dataclass
class Vendor:
    vendor_id: str
    name: str
    coi_required: bool


@dataclass
class Decision:
    file: str
    doc_type: str
    vendor_id: str = ""
    vendor: str = ""
    decision: str = "APPROVED"
    reasons: list[tuple[str, str]] = field(default_factory=list)   # (code, plain text): HOLD reasons
    notes: list[tuple[str, str]] = field(default_factory=list)     # (code, plain text): FYI only
    data: dict = field(default_factory=dict)

    def hold(self, code, detail=""):
        self.decision = "HOLD"
        self.reasons.append((code, REASONS[code].format(detail=detail)))

    def note(self, code, detail=""):
        self.notes.append((code, REASONS[code].format(detail=detail)))


def load_vendors(path: pathlib.Path) -> dict[str, Vendor]:
    with open(path) as f:
        return {r["vendor_id"]: Vendor(r["vendor_id"], r["vendor_name"], r["coi_required"] == "yes") for r in csv.DictReader(f)}


def load_pos(path: pathlib.Path) -> dict[str, dict]:
    with open(path) as f:
        return {r["po_number"].upper(): {"vendor_id": r["vendor_id"], "amount": float(r["amount"]), "status": r["status"]}
                for r in csv.DictReader(f)}


def _norm(name: str) -> str:
    name = re.sub(r"[^a-z0-9 ]", " ", (name or "").lower())
    return " ".join(w for w in name.split() if w not in {"llc", "inc", "co", "ltd", "the", "and"})


def match_vendor(name: str | None, vendors: dict[str, Vendor]) -> Vendor | None:
    """Names on paper vary ("KAPENA LINEN SERVICE", "Kapena Linen Service LLC"), so compare loosely."""
    if not name:
        return None
    best, score = None, 0.0
    for v in vendors.values():
        s = difflib.SequenceMatcher(None, _norm(name), _norm(v.name)).ratio()
        if s > score:
            best, score = v, s
    return best if score >= 0.85 else None


def _parse_date(s):
    try:
        return date.fromisoformat(s) if s else None
    except ValueError:
        return None


def money(x):
    return f"-${-x:,.2f}" if x < 0 else f"${x:,.2f}"


def check_coi(d: Decision, as_of: date) -> None:
    """Insurance certificates are recorded, not paid. Problems are noted and show up on the vendor's invoices."""
    x = d.data
    exp = _parse_date(x.get("policy_expiration"))
    if not d.vendor_id:
        d.hold("UNKNOWN_VENDOR", x.get("vendor_name") or "(none)")
    if exp is None:
        d.hold("INCOMPLETE", "no expiration date")


def coi_problems(coi: dict | None, as_of: date) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """For a contractor's invoice: (hold reasons, notes) from the latest certificate on file."""
    if coi is None:
        return [("COI_MISSING", "")], []
    holds, notes = [], []
    exp = _parse_date(coi.get("policy_expiration"))
    if exp and exp < as_of:
        holds.append(("COI_EXPIRED", f"{exp:%b %d, %Y} ({(as_of - exp).days} days ago)"))
    elif exp and (exp - as_of).days <= COI_WARNING_DAYS:
        notes.append(("COI_EXPIRING", f"in {(exp - as_of).days} days ({exp:%b %d, %Y}): request a renewal"))
    limit = coi.get("each_occurrence_limit")
    if limit is not None and limit < MIN_EACH_OCCURRENCE:
        holds.append(("COI_COVERAGE_LOW", f"{money(limit)} per occurrence is below the required {money(MIN_EACH_OCCURRENCE)}"))
    return holds, notes


def check_invoice(d: Decision, pos: dict, vendors: dict[str, Vendor], seen: list[Decision], cois: dict, as_of: date) -> None:
    x = d.data
    missing = [k for k in ("vendor_name", "invoice_number", "total") if x.get(k) in (None, "")]
    if missing:
        d.hold("INCOMPLETE", ", ".join(missing))
        return
    if not d.vendor_id:
        d.hold("UNKNOWN_VENDOR", x["vendor_name"])

    # Duplicates: compare with invoices already seen in this batch (earliest received wins).
    for prev in seen:
        p = prev.data
        if prev.vendor_id != d.vendor_id:
            continue
        if (p.get("invoice_number") or "").upper() == x["invoice_number"].upper():
            d.hold("DUPLICATE", f"{prev.file} (same invoice number {x['invoice_number']})")
            break
        if p.get("total") == x["total"] and p.get("invoice_date") == x.get("invoice_date"):
            d.hold("POSSIBLE_DUPLICATE", f"{prev.file} (same vendor, amount {money(x['total'])} and date, different invoice number)")
            break

    # Purchase order
    po_num = (x.get("po_number") or "").strip().upper()
    if not po_num:
        d.hold("MISSING_PO")
    elif po_num not in pos:
        d.hold("PO_NOT_FOUND", po_num)
    elif d.vendor_id and pos[po_num]["vendor_id"] != d.vendor_id:
        owner = vendors.get(pos[po_num]["vendor_id"])
        d.hold("PO_VENDOR_MISMATCH", f"{po_num} belongs to {owner.name if owner else pos[po_num]['vendor_id']}, not {d.vendor}")
    else:
        po_amt = pos[po_num]["amount"]
        over = (x["total"] - po_amt) / po_amt if po_amt else 0
        if over > PO_TOLERANCE:
            d.hold("AMOUNT_OVER_PO", f"Amount {money(x['total'])} vs PO {money(po_amt)} (+{over:.1%}, limit {PO_TOLERANCE:.0%})")
        elif over > 0.0005:
            d.note("WITHIN_TOLERANCE", f"{over:.1%} over PO ({money(x['total'])} vs {money(po_amt)}), within the {PO_TOLERANCE:.0%} limit")

    # Does it add up? Lines, then subtotal - discount + tax = total.
    problems = []
    lines = x.get("line_items") or []
    for li in lines:
        q, p, a = li.get("quantity"), li.get("unit_price"), li.get("amount")
        if None not in (q, p, a) and abs(q * p - a) > MATH_TOLERANCE:
            problems.append(f"line \"{li['description']}\" {q:g} x {money(p)} = {money(q * p)}, not {money(a)}")
    line_sum = round(sum(li.get("amount") or 0 for li in lines), 2)
    sub = x.get("subtotal") if x.get("subtotal") is not None else line_sum
    if lines and abs(line_sum - sub) > MATH_TOLERANCE:
        problems.append(f"lines add to {money(line_sum)}, subtotal says {money(sub)}")
    expected = round(sub - (x.get("discount") or 0) + (x.get("tax") or 0), 2)
    if abs(expected - x["total"]) > MATH_TOLERANCE:
        problems.append(f"subtotal - discount + tax = {money(expected)}, total says {money(x['total'])}")
    if problems:
        d.hold("MATH_ERROR", "; ".join(problems))

    # Contractors working on site must have current insurance.
    v = vendors.get(d.vendor_id)
    if v and v.coi_required:
        holds, notes = coi_problems(cois.get(v.vendor_id), as_of)
        for code, detail in holds:
            d.hold(code, detail)
        for code, detail in notes:
            d.note(code, detail)


def run_checks(extractions: list[dict], vendors: dict[str, Vendor], pos: dict, as_of: date) -> list[Decision]:
    """extractions: in the order the documents were received. Certificates are read first, so an invoice
    and its vendor's certificate can arrive in the same batch."""
    decisions = []
    for e in extractions:
        x = e.get("data") or {}
        d = Decision(file=e["file"], doc_type=x.get("doc_type", "UNREADABLE"), data=x)
        v = match_vendor(x.get("vendor_name"), vendors)
        if v:
            d.vendor_id, d.vendor = v.vendor_id, v.name
        else:
            d.vendor = x.get("vendor_name") or ""
        decisions.append(d)

    cois = {}
    for d in decisions:
        if d.doc_type == "COI" and d.vendor_id:
            prev = cois.get(d.vendor_id)
            if prev is None or (d.data.get("policy_expiration") or "") > (prev.get("policy_expiration") or ""):
                cois[d.vendor_id] = d.data            # keep the latest-expiring certificate per vendor

    seen = []
    for e, d in zip(extractions, decisions):
        if e.get("data") is None:
            d.hold("UNREADABLE", e.get("error") or "unknown error")
        elif d.doc_type == "OTHER":
            d.hold("NOT_AN_INVOICE")
        elif d.doc_type == "COI":
            check_coi(d, as_of)
            holds, notes = coi_problems(d.data, as_of)
            d.notes += [(c, REASONS[c].format(detail=t)) for c, t in holds + notes]   # FYI on the certificate itself
        else:
            check_invoice(d, pos, vendors, seen, cois, as_of)
            seen.append(d)
    return decisions
