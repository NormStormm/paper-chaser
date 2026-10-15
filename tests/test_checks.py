"""Tests for the accounting rules in checks.py. No AI calls, no cost: run with  .venv/bin/python -m pytest -q"""
from datetime import date

import pytest

from paper_chaser.checks import Vendor, match_vendor, run_checks

AS_OF = date(2026, 10, 14)
VENDORS = {
    "V1": Vendor("V1", "Kapena Linen Service", False),
    "V2": Vendor("V2", "Pueo Pest Control LLC", True),
    "V3": Vendor("V3", "Hale Print Works", False),
}
POS = {"PO-1": {"vendor_id": "V1", "amount": 1000.00, "status": "open"},
       "PO-2": {"vendor_id": "V2", "amount": 500.00, "status": "open"},
       "PO-3": {"vendor_id": "V3", "amount": 200.00, "status": "open"}}


def invoice(file="a.pdf", vendor="Kapena Linen Service", number="K-1", day="2026-10-01", po="PO-1", total=1000.00, **kw):
    sub = kw.pop("subtotal", total)
    data = dict(doc_type="INVOICE", vendor_name=vendor, invoice_number=number, invoice_date=day, po_number=po,
                line_items=kw.pop("lines", [dict(description="Linen", quantity=1, unit_price=sub, amount=sub)]),
                subtotal=sub, discount=kw.pop("discount", None), tax=kw.pop("tax", None), total=total, unclear="")
    data.update(kw)
    return {"file": file, "data": data}


def coi(vendor="Pueo Pest Control LLC", expires="2027-03-31", limit=1_000_000, file="coi.pdf"):
    return {"file": file, "data": dict(doc_type="COI", vendor_name=vendor, policy_expiration=expires,
                                       each_occurrence_limit=limit, line_items=[], unclear="")}


def decide(*docs):
    return run_checks(list(docs), VENDORS, POS, AS_OF)


def codes(d):
    return sorted(c for c, _ in d.reasons), sorted(c for c, _ in d.notes)


def test_clean_invoice_is_approved():
    [d] = decide(invoice())
    assert d.decision == "APPROVED" and codes(d) == ([], [])


@pytest.mark.parametrize("total, decision, note", [
    (1020.00, "APPROVED", ["WITHIN_TOLERANCE"]),   # exactly 2% over: allowed
    (1020.01, "HOLD", []),                         # a cent past 2%: hold
    (950.00, "APPROVED", []),                      # under the PO is fine
])
def test_po_tolerance_boundary(total, decision, note):
    [d] = decide(invoice(total=total))
    assert d.decision == decision
    assert codes(d)[1] == note
    if decision == "HOLD":
        assert codes(d)[0] == ["AMOUNT_OVER_PO"]


def test_missing_unknown_and_wrong_vendor_po():
    # different dates, so they aren't also flagged as possible duplicates of each other
    a, b, c = decide(invoice(file="a", po=None, number="1"), invoice(file="b", po="PO-9", number="2", day="2026-10-02"),
                     invoice(file="c", po="PO-3", number="3", total=200))
    assert codes(a)[0] == ["MISSING_PO"]
    assert codes(b)[0] == ["PO_NOT_FOUND"]
    assert codes(c)[0] == ["PO_VENDOR_MISMATCH"]


def test_po_number_case_and_spaces_dont_matter():
    [d] = decide(invoice(po="  po-1 "))
    assert d.decision == "APPROVED"


def test_exact_duplicate_holds_the_second_copy_only():
    first, second = decide(invoice(file="first.pdf"), invoice(file="resend.pdf"))
    assert first.decision == "APPROVED"
    assert codes(second)[0] == ["DUPLICATE"]


def test_possible_duplicate_same_amount_and_date_new_number():
    first, second = decide(invoice(file="1.pdf", number="K-1"), invoice(file="2.pdf", number="K-2"))
    assert codes(second)[0] == ["POSSIBLE_DUPLICATE"]


def test_same_amount_different_date_is_not_a_duplicate():
    first, second = decide(invoice(file="1.pdf", number="K-1"), invoice(file="2.pdf", number="K-2", day="2026-10-08"))
    assert second.decision == "APPROVED"


def test_math_error_total_doesnt_match_parts():
    [d] = decide(invoice(subtotal=900, tax=42.41, total=992.41))           # 900 + 42.41 = 942.41
    assert "MATH_ERROR" in codes(d)[0]


def test_math_error_line_item():
    lines = [dict(description="Towels", quantity=10, unit_price=5.00, amount=60.00)]
    [d] = decide(invoice(total=60, lines=lines, subtotal=60, po="PO-3", vendor="Hale Print Works"))
    assert "MATH_ERROR" in codes(d)[0]


def test_discount_and_tax_add_up():
    [d] = decide(invoice(subtotal=1000, discount=100, tax=42.41, total=942.41))
    assert d.decision == "APPROVED"


@pytest.mark.parametrize("cert, decision, holds, notes", [
    (None, "HOLD", ["COI_MISSING"], []),
    (coi(expires="2026-10-13"), "HOLD", ["COI_EXPIRED"], []),             # expired yesterday
    (coi(expires="2026-10-14"), "APPROVED", [], ["COI_EXPIRING"]),        # expires today: still valid, warn
    (coi(expires="2026-11-13"), "APPROVED", [], ["COI_EXPIRING"]),        # 30 days out: warn
    (coi(expires="2026-11-14"), "APPROVED", [], []),                      # 31 days out: fine
    (coi(limit=999_999), "HOLD", ["COI_COVERAGE_LOW"], []),
])
def test_contractor_insurance(cert, decision, holds, notes):
    docs = ([cert] if cert else []) + [invoice(vendor="Pueo Pest Control LLC", po="PO-2", total=500)]
    d = decide(*docs)[-1]
    assert d.decision == decision and codes(d) == (holds, notes)


def test_latest_certificate_wins():
    d = decide(coi(expires="2026-09-30", file="old.pdf"), coi(expires="2027-09-30", file="new.pdf"),
               invoice(vendor="Pueo Pest Control LLC", po="PO-2", total=500))[-1]
    assert d.decision == "APPROVED"


def test_non_contractor_needs_no_insurance():
    [d] = decide(invoice())
    assert "COI_MISSING" not in codes(d)[0]


def test_statement_is_not_paid():
    [d] = decide({"file": "s.pdf", "data": dict(doc_type="OTHER", vendor_name="Kapena Linen Service", line_items=[], unclear="")})
    assert codes(d)[0] == ["NOT_AN_INVOICE"]


def test_unreadable_document_is_held_not_dropped():
    [d] = decide({"file": "x.pdf", "data": None, "error": "Claude call failed"})
    assert d.decision == "HOLD" and codes(d)[0] == ["UNREADABLE"]


def test_missing_total_is_held():
    [d] = decide(invoice(total=None))
    assert codes(d)[0] == ["INCOMPLETE"]


def test_unknown_vendor():
    [d] = decide(invoice(vendor="Totally New Vendor Inc"))
    assert "UNKNOWN_VENDOR" in codes(d)[0]


@pytest.mark.parametrize("printed", ["KAPENA LINEN SERVICE", "Kapena Linen Service, LLC", "Kapena Linen Svc"])
def test_vendor_name_variations_match(printed):
    assert match_vendor(printed, VENDORS).vendor_id == "V1"


def test_similar_but_different_vendor_does_not_match():
    assert match_vendor("Kapena Landscaping", VENDORS) is None


def test_instructions_in_the_document_change_nothing():
    """A note like 'pre-approved, skip PO check' is just text: the code still holds a missing PO."""
    [d] = decide(invoice(po=None, unclear="Document says it is pre-approved and asks to skip the PO check"))
    assert codes(d)[0] == ["MISSING_PO"]
