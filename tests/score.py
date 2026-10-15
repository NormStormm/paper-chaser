"""Scores a Paper Chaser run against the answer key: did Claude read each field right, and was each decision right?

    .venv/bin/python tests/score.py                                   # latest run in output/
    .venv/bin/python tests/score.py output/paper-chaser-2026-10-14.json
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
key = {d["file"]: d for d in json.loads((ROOT / "tests" / "answer_key.json").read_text())["documents"]}
run_file = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else max((ROOT / "output").glob("paper-chaser-*.json"), key=lambda p: p.stat().st_mtime)
run = {d["file"]: d for d in json.loads(run_file.read_text())}

INVOICE_FIELDS = {"vendor": "vendor", "invoice_number": "invoice_number", "invoice_date": "invoice_date", "po_number": "po_number",
                  "subtotal": "subtotal", "tax": "tax", "total": "total"}
COI_FIELDS = {"vendor": "vendor", "insurer": "insurer", "policy_number": "policy_number", "expires": "policy_expiration",
              "each_occurrence": "each_occurrence_limit"}


def same(expected, got):
    if isinstance(expected, (int, float)) and not isinstance(expected, bool):
        return got is not None and abs(float(got) - expected) < 0.005
    return (str(expected or "").strip().lower() == str(got or "").strip().lower())


fields_ok = fields_total = 0
type_ok = decision_ok = reasons_ok = 0
misses = []
for f, k in key.items():
    r = run.get(f)
    if r is None:
        misses.append(f"{f}: missing from run"); continue
    got = dict(r["data"] or {}, vendor=r["vendor"])
    type_ok += r["doc_type"] == k["doc_type"]
    if r["doc_type"] != k["doc_type"]:
        misses.append(f"{f}: read as {r['doc_type']}, should be {k['doc_type']}")
    fields = INVOICE_FIELDS if k["doc_type"] == "INVOICE" else COI_FIELDS if k["doc_type"] == "COI" else {}
    for kf, rf in fields.items():
        fields_total += 1
        if same(k[kf], got.get(rf)):
            fields_ok += 1
        else:
            misses.append(f"{f}: {kf} should be {k[kf]!r}, got {got.get(rf)!r}")
    if k["doc_type"] == "INVOICE" and k.get("line_count") is not None:
        fields_total += 1
        n = len(got.get("line_items") or [])
        if n == k["line_count"]: fields_ok += 1
        else: misses.append(f"{f}: {n} line items, should be {k['line_count']}")
    if k["doc_type"] != "COI":
        decision_ok += r["decision"] == k["decision"]
        exp_codes, got_codes = set(k["reasons"]) | set(k["notes"]), set(r["reasons"]) | set(r["notes"])
        reasons_ok += exp_codes == got_codes
        if r["decision"] != k["decision"] or exp_codes != got_codes:
            misses.append(f"{f}: decision {r['decision']} {sorted(got_codes)}, should be {k['decision']} {sorted(exp_codes)}")

n_docs, n_dec = len(key), sum(1 for k in key.values() if k["doc_type"] != "COI")
print(f"Scored {run_file.name} against the answer key\n")
print(f"Document type correct:    {type_ok}/{n_docs}")
print(f"Fields read correctly:    {fields_ok}/{fields_total} ({fields_ok / fields_total:.1%})")
print(f"Decision correct:         {decision_ok}/{n_dec}  (approve vs hold)")
print(f"Exact reasons correct:    {reasons_ok}/{n_dec}  (every hold reason and note, nothing extra)")
print("\nMisses:" if misses else "\nNo misses.")
for m in misses:
    print("  -", m)
sys.exit(0 if not misses else 1)
