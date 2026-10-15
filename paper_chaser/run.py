"""Run Paper Chaser on a folder of PDFs.

    .venv/bin/python -m paper_chaser.run                      # inbox/ -> output/paper-chaser-<date>.xlsx
    .venv/bin/python -m paper_chaser.run --as-of 2026-10-14   # check expiry dates against a fixed day
    .venv/bin/python -m paper_chaser.run --refresh            # re-read every PDF instead of reusing saved reads

Needs ANTHROPIC_API_KEY in .env (never committed). Documents are handled in the order they were
received (file time), so the first copy of a duplicate is the one that passes.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
from concurrent.futures import ThreadPoolExecutor
from datetime import date

from dotenv import load_dotenv

from . import checks, extract, report

ROOT = pathlib.Path(__file__).resolve().parent.parent
PRICE = {"claude-opus-5-5": (4, 20), "claude-sonnet-5-5": (2, 10), "claude-haiku-5-5": (0.10, 0.50)}  # $ per 1M tokens


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--inbox", default=str(ROOT / "inbox"))
    ap.add_argument("--as-of", default=date.today().isoformat(), help="date to check insurance expiry against (YYYY-MM-DD)")
    ap.add_argument("--model", default=extract.MODEL)
    ap.add_argument("--refresh", action="store_true", help="re-read PDFs even if a saved read exists")
    ap.add_argument("--out", default=None, help="output .xlsx path")
    args = ap.parse_args(argv)

    load_dotenv(ROOT / ".env")
    as_of = date.fromisoformat(args.as_of)
    pdfs = sorted(pathlib.Path(args.inbox).glob("*.pdf"), key=lambda p: (p.stat().st_mtime_ns, p.name))
    if not pdfs:
        print("No PDFs in", args.inbox)
        return 1
    client = None
    if os.environ.get("ANTHROPIC_API_KEY"):
        import anthropic
        client = anthropic.Anthropic()
    else:
        print("No ANTHROPIC_API_KEY found in .env: only saved reads can be used.")

    print(f"Reading {len(pdfs)} PDFs with {args.model} …")
    cache = ROOT / "output" / "extracted"
    with ThreadPoolExecutor(max_workers=4) as pool:      # 4 at a time: fast, and gentle on rate limits
        extractions = list(pool.map(lambda p: extract.extract_cached(p, cache, client, args.model, args.refresh), pdfs))

    vendors = checks.load_vendors(ROOT / "data" / "vendors.csv")
    pos = checks.load_pos(ROOT / "data" / "purchase_orders.csv")
    decisions = checks.run_checks(extractions, vendors, pos, as_of)

    out = pathlib.Path(args.out) if args.out else ROOT / "output" / f"paper-chaser-{as_of.isoformat()}.xlsx"
    summary = report.write_workbook(out, decisions, extractions, as_of, args.model)
    (out.with_suffix(".json")).write_text(json.dumps(
        [{"file": d.file, "doc_type": d.doc_type, "vendor": d.vendor, "decision": d.decision,
          "reasons": [c for c, _ in d.reasons], "notes": [c for c, _ in d.notes], "data": d.data} for d in decisions], indent=1))

    new = [e for e in extractions if not e.get("cached")]
    pi, po = PRICE.get(args.model, (0, 0))
    cost = sum(e["input_tokens"] * pi + e["output_tokens"] * po for e in new) / 1e6
    for d in decisions:
        label = "RECORDED" if d.doc_type == "COI" and d.decision == "APPROVED" else d.decision
        mark = {"APPROVED": "✓", "RECORDED": "•", "HOLD": "✗"}.get(label, "?")
        why = "; ".join(t for _, t in d.reasons) or "; ".join(t for _, t in d.notes)
        print(f"  {mark} {label:<8} {d.doc_type:<7} {d.file[:38]:<38} {why[:90]}")
    print(f"\nApproved {summary['approved']} invoices (${summary['amount_approved']:,.2f}), {summary['held']} on hold, "
          f"{summary['cois']} insurance certificates recorded.")
    print(f"Read {len(new)} new PDFs (${cost:.3f}); reused {len(extractions) - len(new)} saved reads.")
    print(f"Wrote {out.relative_to(ROOT) if out.is_relative_to(ROOT) else out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
