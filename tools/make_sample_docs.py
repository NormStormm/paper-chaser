"""Creates the fake test paperwork for Paper Chaser, plus the answer key.

    .venv/bin/python tools/make_sample_docs.py

Writes:
  data/vendors.csv, data/purchase_orders.csv   - the "accounting system" the checks compare against
  inbox/*.pdf                                  - 25 documents: invoices, insurance certificates, one stray
  tests/answer_key.json                        - what each document says and what the right decision is

Every vendor, person, policy and amount is fictitious. Problems are planted on purpose
(overcharge, duplicate, missing PO, bad math, expired insurance...) so we know the right answer.
"""
import csv
import json
import pathlib
import random
from datetime import date

from PIL import Image, ImageDraw, ImageFilter, ImageFont
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

ROOT = pathlib.Path(__file__).resolve().parent.parent
INBOX, DATA, TESTS = ROOT / "inbox", ROOT / "data", ROOT / "tests"
AS_OF = date(2026, 10, 14)          # the "today" the answer key assumes
GET_RATE = 0.04712                  # Hawaii general excise tax pass-on rate (Oahu)
BILL_TO = ["Kaimana Demo Resort (fictitious)", "Attn: Accounts Payable", "100 Example Beach Rd", "Honolulu, HI 96815"]
FOOTER = "SAMPLE DOCUMENT - fictitious vendor, created for software testing"
random.seed(7)

VENDORS = [  # id, name, address, needs insurance certificate (contractors working on site)
    ("V01", "Kapena Linen Service", "88 Laundry Ln, Kapolei, HI 96707", False),
    ("V02", "Ewa Plains Produce Co.", "12 Farm Rd, Ewa Beach, HI 96706", False),
    ("V03", "Koolau Coffee Roasters", "450 Ridge St, Kaneohe, HI 96744", False),
    ("V04", "Pueo Pest Control LLC", "7 Owl Way, Pearl City, HI 96782", True),
    ("V05", "Mauka Air & Refrigeration", "301 Upland Ave, Mililani, HI 96789", True),
    ("V06", "Leeward Line Electric", "55 Current Ct, Waipahu, HI 96797", True),
    ("V07", "Lanikai Pool Services", "19 Lagoon Dr, Kailua, HI 96734", True),
    ("V08", "Kalo Paper & Janitorial Supply", "900 Supply Blvd, Honolulu, HI 96819", False),
    ("V09", "Makai Fish Market Wholesale", "2 Pier Rd, Honolulu, HI 96817", False),
    ("V10", "Hale Print Works", "64 Press St, Honolulu, HI 96813", False),
    ("V11", "Nalu Landscaping", "33 Green Way, Waimanalo, HI 96795", True),
]
VNAME = {v[0]: v[1] for v in VENDORS}


def money(x):
    return f"-${-x:,.2f}" if x < 0 else f"${x:,.2f}"


def totals(lines, discount_pct=0.0, add_error=0.0):
    sub = round(sum(q * p for _, q, p in lines), 2)
    disc = round(sub * discount_pct, 2)
    tax = round((sub - disc) * GET_RATE, 2)
    real_total = round(sub - disc + tax, 2)
    return {"subtotal": sub, "discount": disc, "tax": tax, "total": round(real_total + add_error, 2), "real_total": real_total}


# ── Invoices: (file, vendor, invoice #, date, PO #, lines, options, expected decision, reasons) ──
I = []
def inv(file, vid, number, d, po, lines, template="A", discount=0.0, add_error=0.0, scanned=False, due_days=30,
        decision="APPROVED", reasons=(), notes=()):
    t = totals(lines, discount, add_error)
    I.append(dict(file=file, vendor_id=vid, vendor=VNAME[vid], invoice_number=number, invoice_date=d, po_number=po,
                  lines=lines, template=template, scanned=scanned, due_days=due_days, **t,
                  decision=decision, reasons=list(reasons), notes=list(notes)))

inv("Invoice_KLS-10233.pdf", "V01", "KLS-10233", "2026-10-01", "PO-24101",
    [("Bath towels, 27x54, white", 300, 2.15), ("Queen flat sheets, 250 TC", 120, 6.25), ("Pillowcases, standard", 200, 1.10)])
inv("EPP-5571.pdf", "V02", "EPP-5571", "2026-10-03", "PO-24102",
    [("Romaine hearts, case", 14, 38.50), ("Maui onions, 25 lb", 6, 41.00), ("Papaya, case", 9, 29.75), ("Herb mix, flat", 4, 22.00)], template="B")
inv("koolau_inv_0918.pdf", "V03", "KCR-0918", "2026-10-02", "PO-24103",
    [("Kona blend whole bean, 5 lb", 24, 61.00), ("Decaf whole bean, 5 lb", 6, 64.50)], template="C")
inv("PPC-2026-114.pdf", "V04", "PPC-2026-114", "2026-10-06", "PO-24104",
    [("Monthly pest service - guest floors", 1, 1450.00), ("Kitchen treatment (after hours)", 1, 380.00)])
inv("KPJ-77812.pdf", "V08", "KPJ-77812", "2026-10-05", "PO-24105",
    [("Toilet tissue 2-ply, case of 96", 18, 54.20), ("Hand soap refill 1L, case", 10, 47.80), ("Trash liners 33 gal, case", 12, 31.15)], template="B",
    decision="APPROVED", notes=["WITHIN_TOLERANCE"])
inv("MFW-3301.pdf", "V09", "MFW-3301", "2026-10-07", "PO-24106",
    [("Ahi tuna, sashimi grade, lb", 40, 24.50), ("Mahi mahi fillet, lb", 35, 16.75), ("Opakapaka, whole, lb", 20, 14.40)], template="C",
    decision="HOLD", reasons=["AMOUNT_OVER_PO"])
inv("HPW-1188.pdf", "V10", "HPW-1188", "2026-10-04", "",
    [("Guest directory printing, 64 pp", 250, 3.40), ("Door hangers, 2-sided", 2000, 0.09)],
    decision="HOLD", reasons=["MISSING_PO"])
inv("EPP-5590.pdf", "V02", "EPP-5590", "2026-10-08", "PO-29999",
    [("Lettuce mix, case", 10, 36.00), ("Tomatoes, 25 lb", 5, 44.25)], template="B",
    decision="HOLD", reasons=["PO_NOT_FOUND"])
inv("FW_ Invoice KLS-10233 (resend).pdf", "V01", "KLS-10233", "2026-10-01", "PO-24101",
    [("Bath towels, 27x54, white", 300, 2.15), ("Queen flat sheets, 250 TC", 120, 6.25), ("Pillowcases, standard", 200, 1.10)],
    decision="HOLD", reasons=["DUPLICATE"])
inv("KCR-0931.pdf", "V03", "KCR-0931", "2026-10-09", "PO-24107",
    [("Kona blend whole bean, 5 lb", 20, 61.00), ("Cold brew concentrate, 2.5 gal", 8, 48.00)], template="C", add_error=50.00,
    decision="HOLD", reasons=["MATH_ERROR", "AMOUNT_OVER_PO"])  # stated total is $50 over the real sum, so also ~3% over the PO
inv("MAR-4410.pdf", "V05", "MAR-4410", "2026-10-06", "PO-24108",
    [("Walk-in cooler compressor repair", 1, 2240.00), ("Refrigerant R-448A, lb", 18, 32.50), ("After-hours labor, hr", 4, 145.00)], template="B",
    decision="HOLD", reasons=["COI_EXPIRED"])
inv("LLE-2207.pdf", "V06", "LLE-2207", "2026-10-08", "PO-24109",
    [("Ballroom lighting circuit repair", 1, 860.00), ("LED fixtures, 4 ft", 12, 74.00)],
    decision="APPROVED", notes=["COI_EXPIRING"])
inv("LPS-0612.pdf", "V07", "LPS-0612", "2026-10-01", "PO-24110",
    [("Pool chemical service, October", 1, 1180.00), ("Pump seal replacement", 1, 265.00)], template="C",
    decision="HOLD", reasons=["COI_COVERAGE_LOW"])
inv("NL-3005.pdf", "V11", "NL-3005", "2026-10-10", "PO-24111",
    [("Grounds maintenance, October", 1, 3200.00), ("Hedge trimming, lanai", 1, 420.00)], template="B",
    decision="HOLD", reasons=["COI_MISSING"])
inv("scan_0042.pdf", "V09", "MFW-3315", "2026-10-11", "PO-24112",
    [("Shrimp 16/20, lb", 30, 13.25), ("Ahi poke cubes, lb", 25, 19.00)], scanned=True)
inv("KPJ-77830.pdf", "V08", "KPJ-77830", "2026-10-09", "PO-24113",
    [("Glass cleaner, case", 6, 39.90), ("Microfiber cloths, 50 pk", 8, 27.50)], template="B",
    decision="HOLD", reasons=["PO_VENDOR_MISMATCH"])
inv("HPW-1192.pdf", "V10", "HPW-1192", "2026-10-10", "PO-24114",
    [("Banquet menus, cardstock", 400, 1.85), ("Table numbers, laminated", 60, 4.20), ("Rush fee", 1, 75.00)], discount=0.10)
inv("Ewa Plains invoice.pdf", "V02", "EPP-5594", "2026-10-03", "PO-24115",
    [("Romaine hearts, case", 14, 38.50), ("Maui onions, 25 lb", 6, 41.00), ("Papaya, case", 9, 29.75), ("Herb mix, flat", 4, 22.00)], template="B",
    decision="HOLD", reasons=["POSSIBLE_DUPLICATE"])
inv("KCR-0940.pdf", "V03", "KCR-0940", "2026-10-12", "PO-24116",
    [("Kona blend whole bean, 5 lb", 18, 61.00), ("Vanilla syrup, 1L", 12, 9.80)], template="C")
inv("PPC-2026-121.pdf", "V04", "PPC-2026-121", "2026-10-12", "PO-24117",
    [("Rodent bait station service", 1, 540.00)])

# Purchase orders: normally equal to the invoice total; a few set up to trip a check.
PO = {}
for x in I:
    if x["po_number"] and x["po_number"] not in ("PO-29999",):
        PO.setdefault(x["po_number"], [x["vendor_id"], x["real_total"]])
PO["PO-24105"][1] = round(next(x for x in I if x["invoice_number"] == "KPJ-77812")["total"] / 1.015, 2)  # invoice 1.5% over: OK
PO["PO-24106"][1] = 1790.00                                                                              # invoice ~8.5% over: hold
PO["PO-24113"][0] = "V10"                                                                                # PO belongs to Hale Print
PO["PO-24118"] = ["V07", 900.00]                                                                         # an open PO nobody billed yet

# ── Insurance certificates ──
C = [
    dict(file="COI_PueoPest_2026.pdf", vendor_id="V04", insurer="Fictional Mutual Insurance Co.", policy="GL-PPC-882341",
         effective="2026-04-01", expires="2027-03-31", each_occurrence=1_000_000, aggregate=2_000_000, scanned=False),
    dict(file="scan_0051.pdf", vendor_id="V05", insurer="Example Casualty Group", policy="CGL-55190-MA",
         effective="2025-10-01", expires="2026-09-30", each_occurrence=2_000_000, aggregate=4_000_000, scanned=True),
    dict(file="LeewardLine_COI.pdf", vendor_id="V06", insurer="Sample Indemnity Ltd.", policy="LL-10992-E",
         effective="2025-10-26", expires="2026-10-26", each_occurrence=1_000_000, aggregate=2_000_000, scanned=False),
    dict(file="Lanikai Pool - certificate of insurance.pdf", vendor_id="V07", insurer="Fictional Mutual Insurance Co.", policy="GL-LPS-30117",
         effective="2026-05-01", expires="2027-05-01", each_occurrence=500_000, aggregate=1_000_000, scanned=False),
]
for c in C:
    c["vendor"] = VNAME[c["vendor_id"]]
OTHER = dict(file="Kapena_statement_Sept.pdf", vendor_id="V01")


# ── Drawing ──
def draw_invoice_pdf(path, x):
    c = canvas.Canvas(str(path), pagesize=letter)
    W, H = letter
    v = next(v for v in VENDORS if v[0] == x["vendor_id"])
    t = x["template"]
    if t == "A":    # classic: vendor block top left, INVOICE top right
        c.setFont("Helvetica-Bold", 18); c.drawString(50, H - 60, v[1])
        c.setFont("Helvetica", 10); c.drawString(50, H - 76, v[2])
        c.setFont("Helvetica-Bold", 26); c.drawRightString(W - 50, H - 62, "INVOICE")
        c.setFont("Helvetica", 10)
        c.drawRightString(W - 50, H - 82, f"Invoice #: {x['invoice_number']}")
        c.drawRightString(W - 50, H - 96, f"Date: {x['invoice_date']}")
        if x["po_number"]: c.drawRightString(W - 50, H - 110, f"PO #: {x['po_number']}")
        y = H - 150
    elif t == "B":  # bill-to first, details in a box
        c.setFillColor(colors.HexColor("#1f4e79")); c.rect(0, H - 90, W, 90, fill=1, stroke=0)
        c.setFillColor(colors.white); c.setFont("Helvetica-Bold", 20); c.drawString(50, H - 50, v[1].upper())
        c.setFont("Helvetica", 9); c.drawString(50, H - 68, v[2]); c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 12); c.drawString(W - 230, H - 120, "Tax Invoice")
        c.setFont("Helvetica", 10)
        c.drawString(W - 230, H - 136, f"No. {x['invoice_number']}")
        c.drawString(W - 230, H - 150, f"Issued {date.fromisoformat(x['invoice_date']).strftime('%B %d, %Y')}")
        c.drawString(W - 230, H - 164, f"Your order: {x['po_number']}" if x["po_number"] else "Your order: (none given)")
        y = H - 120
    else:           # minimal, everything in one line
        c.setFont("Courier-Bold", 14); c.drawString(50, H - 60, f"{v[1]} -- Invoice {x['invoice_number']}")
        c.setFont("Courier", 10)
        c.drawString(50, H - 78, f"{v[2]}  |  Date {date.fromisoformat(x['invoice_date']).strftime('%m/%d/%Y')}  |  Ref {x['po_number'] or '-'}")
        y = H - 110
    c.setFont("Helvetica-Bold", 10); c.drawString(50, y, "Bill to:")
    c.setFont("Helvetica", 10)
    for i, line in enumerate(BILL_TO):
        c.drawString(50, y - 14 * (i + 1), line)
    y -= 100
    c.setFont("Helvetica-Bold", 10)
    for col, label in ((50, "Description"), (340, "Qty"), (400, "Unit price"), (490, "Amount")):
        c.drawString(col, y, label)
    c.line(50, y - 4, W - 50, y - 4)
    c.setFont("Helvetica", 10)
    for desc, q, p in x["lines"]:
        y -= 18
        c.drawString(50, y, desc); c.drawRightString(370, y, f"{q:,}"); c.drawRightString(460, y, money(p)); c.drawRightString(W - 50, y, money(q * p))
    y -= 12; c.line(340, y, W - 50, y)
    rows = [("Subtotal", x["subtotal"])]
    if x["discount"]: rows.append(("Discount (10%)", -x["discount"]))
    rows += [("Hawaii GET (4.712%)", x["tax"]), ("TOTAL DUE", x["total"])]
    for label, amt in rows:
        y -= 18
        c.setFont("Helvetica-Bold" if label == "TOTAL DUE" else "Helvetica", 10)
        c.drawString(360, y, label); c.drawRightString(W - 50, y, money(amt))
    due = date.fromordinal(date.fromisoformat(x["invoice_date"]).toordinal() + x["due_days"])
    c.setFont("Helvetica", 9); c.drawString(50, y - 40, f"Terms: Net {x['due_days']}. Due {due.isoformat()}. Mahalo for your business!")
    c.setFont("Helvetica-Oblique", 7); c.setFillColor(colors.grey); c.drawCentredString(W / 2, 30, FOOTER)
    c.save()


def draw_coi_pdf(path, x):
    c = canvas.Canvas(str(path), pagesize=letter)
    W, H = letter
    c.setFont("Helvetica-Bold", 15); c.drawCentredString(W / 2, H - 55, "CERTIFICATE OF LIABILITY INSURANCE")
    c.setFont("Helvetica", 8)
    c.drawCentredString(W / 2, H - 70, "This certificate is issued as a matter of information only and confers no rights upon the certificate holder.")
    v = next(v for v in VENDORS if v[0] == x["vendor_id"])
    rows = [("Insured", f"{v[1]}, {v[2]}"), ("Insurer", x["insurer"]), ("Type of insurance", "Commercial General Liability (occurrence)"),
            ("Policy number", x["policy"]), ("Policy effective", date.fromisoformat(x["effective"]).strftime("%m/%d/%Y")),
            ("Policy expiration", date.fromisoformat(x["expires"]).strftime("%m/%d/%Y")),
            ("Each occurrence", money(x["each_occurrence"])), ("General aggregate", money(x["aggregate"])),
            ("Certificate holder", "; ".join(BILL_TO[:1] + BILL_TO[2:]))]
    y = H - 110
    for label, val in rows:
        c.setFont("Helvetica-Bold", 10); c.drawString(60, y, label)
        c.setFont("Helvetica", 10); c.drawString(210, y, val)
        c.setStrokeColor(colors.lightgrey); c.line(60, y - 6, W - 60, y - 6)
        y -= 26
    c.setFont("Helvetica", 8); c.setFillColor(colors.black)
    c.drawString(60, y - 20, "Should any of the above policies be cancelled before the expiration date, notice will be delivered per policy provisions.")
    c.setFont("Helvetica-Oblique", 7); c.setFillColor(colors.grey); c.drawCentredString(W / 2, 30, FOOTER)
    c.save()


def draw_statement_pdf(path):
    c = canvas.Canvas(str(path), pagesize=letter)
    W, H = letter
    c.setFont("Helvetica-Bold", 18); c.drawString(50, H - 60, "Kapena Linen Service")
    c.setFont("Helvetica-Bold", 14); c.drawRightString(W - 50, H - 60, "STATEMENT OF ACCOUNT")
    c.setFont("Helvetica", 10); c.drawString(50, H - 90, "Statement period: September 1-30, 2026. This is not an invoice. Please pay from invoices.")
    y = H - 130
    for d, ref, amt in [("2026-09-02", "KLS-10107 (paid)", 1520.40), ("2026-09-16", "KLS-10170 (paid)", 1604.95), ("2026-09-30", "Balance forward", 0.00)]:
        c.drawString(50, y, d); c.drawString(160, y, ref); c.drawRightString(W - 50, y, money(amt)); y -= 18
    c.setFont("Helvetica-Bold", 10); c.drawString(50, y - 10, "Account balance: $0.00")
    c.setFont("Helvetica-Oblique", 7); c.setFillColor(colors.grey); c.drawCentredString(W / 2, 30, FOOTER)
    c.save()


def font(size, bold=False):
    name = "Arial Bold.ttf" if bold else "Arial.ttf"
    return ImageFont.truetype(f"/System/Library/Fonts/Supplemental/{name}", size)


def scanned(path, title_lines, body_lines):
    """Draws a page as an image, then makes it look scanned: slight tilt, grey paper, blur, speckles."""
    img = Image.new("L", (1700, 2200), 246)
    d = ImageDraw.Draw(img)
    y = 120
    for txt, size, bold in title_lines:
        d.text((120, y), txt, fill=25, font=font(size, bold)); y += size + 18
    y += 30
    for txt in body_lines:
        d.text((120, y), txt, fill=35, font=font(30)); y += 46
    d.text((520, 2110), FOOTER, fill=120, font=font(20))
    for _ in range(2500):
        d.point((random.randrange(1700), random.randrange(2200)), fill=random.randrange(120, 200))
    img = img.rotate(random.choice([-1.6, 1.4]), expand=False, fillcolor=246, resample=Image.BICUBIC)
    img = img.filter(ImageFilter.GaussianBlur(0.8))
    img.convert("RGB").save(path, "PDF", resolution=200)


def draw_scanned_invoice(path, x):
    lines = [f"Invoice #: {x['invoice_number']}        Date: {x['invoice_date']}        PO: {x['po_number']}", "",
             "Bill to: " + BILL_TO[0], "", f"{'Description':<34}{'Qty':>6}{'Price':>12}{'Amount':>14}"]
    for desc, q, p in x["lines"]:
        lines.append(f"{desc:<34}{q:>6}{money(p):>12}{money(q * p):>14}")
    lines += ["", f"Subtotal: {money(x['subtotal'])}", f"Hawaii GET 4.712%: {money(x['tax'])}", f"TOTAL DUE: {money(x['total'])}"]
    scanned(path, [(x["vendor"], 54, True), ("INVOICE", 40, True)], lines)


def draw_scanned_coi(path, x):
    lines = [f"Insured: {x['vendor']}", f"Insurer: {x['insurer']}", "Coverage: Commercial General Liability",
             f"Policy number: {x['policy']}", f"Effective: {date.fromisoformat(x['effective']).strftime('%m/%d/%Y')}",
             f"Expiration: {date.fromisoformat(x['expires']).strftime('%m/%d/%Y')}",
             f"Each occurrence: {money(x['each_occurrence'])}", f"General aggregate: {money(x['aggregate'])}",
             f"Certificate holder: {BILL_TO[0]}"]
    scanned(path, [("CERTIFICATE OF LIABILITY INSURANCE", 44, True)], lines)


def main():
    for p in (INBOX, DATA, TESTS):
        p.mkdir(exist_ok=True)
    for old in INBOX.glob("*.pdf"):
        old.unlink()
    for x in I:
        (draw_scanned_invoice if x["scanned"] else draw_invoice_pdf)(INBOX / x["file"], x)
    for x in C:
        (draw_scanned_coi if x["scanned"] else draw_coi_pdf)(INBOX / x["file"], x)
    draw_statement_pdf(INBOX / OTHER["file"])
    # Stamp "received" times a few minutes apart, in the order above, so the first copy of a duplicate
    # is the one that passes. (Cloning from Git resets file times: re-run this script to restore them.)
    import os, time
    start = time.mktime((2026, 10, 13, 8, 0, 0, 0, 0, -1))
    for i, name in enumerate([x["file"] for x in C] + [x["file"] for x in I] + [OTHER["file"]]):
        os.utime(INBOX / name, (start + i * 300, start + i * 300))

    with open(DATA / "vendors.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["vendor_id", "vendor_name", "address", "coi_required"])
        for v in VENDORS: w.writerow([v[0], v[1], v[2], "yes" if v[3] else "no"])
    with open(DATA / "purchase_orders.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["po_number", "vendor_id", "vendor_name", "amount", "status"])
        for po, (vid, amt) in sorted(PO.items()): w.writerow([po, vid, VNAME[vid], f"{amt:.2f}", "open"])

    key = {"as_of": AS_OF.isoformat(), "documents": []}
    for x in I:
        key["documents"].append({
            "file": x["file"], "doc_type": "INVOICE", "vendor": x["vendor"], "invoice_number": x["invoice_number"],
            "invoice_date": x["invoice_date"], "po_number": x["po_number"], "subtotal": x["subtotal"], "discount": x["discount"],
            "tax": x["tax"], "total": x["total"], "line_count": len(x["lines"]),
            "decision": x["decision"], "reasons": x["reasons"], "notes": x["notes"]})
    for x in C:
        key["documents"].append({
            "file": x["file"], "doc_type": "COI", "vendor": x["vendor"], "insurer": x["insurer"], "policy_number": x["policy"],
            "expires": x["expires"], "each_occurrence": x["each_occurrence"]})
    key["documents"].append({"file": OTHER["file"], "doc_type": "OTHER", "vendor": VNAME[OTHER["vendor_id"]],
                             "decision": "HOLD", "reasons": ["NOT_AN_INVOICE"], "notes": []})
    (TESTS / "answer_key.json").write_text(json.dumps(key, indent=1))
    print(f"{len(list(INBOX.glob('*.pdf')))} PDFs in inbox/, {len(PO)} POs, answer key with {len(key['documents'])} documents")


if __name__ == "__main__":
    main()
