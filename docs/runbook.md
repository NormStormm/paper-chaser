# Paper Chaser runbook

How to set it up, run it, read the results, and change the rules.

## Set up (once)

Needs **Python 3.10 or newer** (the current Claude SDK won't install on 3.9, which is what older Macs ship with).

```bash
python3 --version                                   # 3.10+? If not: install from python.org, or use uv (uv python install 3.12)
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

**API key.** Create a key at [console.anthropic.com](https://console.anthropic.com/) → API Keys (one key per project, so you can switch one off without breaking others). Save it in a file named `.env` in this folder:

```bash
read -s "k?Paste your Claude API key: " && printf 'ANTHROPIC_API_KEY=%s\n' "$k" > .env && chmod 600 .env && unset k
```

That prompt (zsh) keeps the key off the screen and out of your shell history. `.env` is listed in `.gitignore`, so Git never uploads it. Never paste the key into code, chat, or a commit.

## Run

```bash
.venv/bin/python -m paper_chaser.run                      # reads inbox/, checks as of today
.venv/bin/python -m paper_chaser.run --as-of 2026-10-14   # check insurance dates against a fixed day (the test set needs this)
.venv/bin/python -m paper_chaser.run --refresh            # re-read every PDF instead of reusing saved reads
.venv/bin/python -m paper_chaser.run --inbox ~/Downloads/invoices --out ~/Desktop/ap-batch.xlsx
```

Output: `output/paper-chaser-<date>.xlsx`, plus a `.json` copy of every decision. Each PDF's read is saved in `output/extracted/`, so **re-running after a rule change costs nothing**. Use `--refresh` only when a PDF itself changed.

**Order matters.** Documents are handled in the order they were received (file modified time), so the first copy of a duplicate passes and later copies are held. Copying files or cloning from Git resets those times. For the test set, re-run `tools/make_sample_docs.py` to restore them.

## Read the results

| Tab | What's on it | Who uses it |
|---|---|---|
| **Summary** | Counts and dollar totals for the batch | Controller / manager |
| **Approved** | Ready to enter for payment. Yellow rows have a note to read (e.g. within PO tolerance, insurance expiring soon). | AP clerk |
| **Exceptions** | Held for a person, with every reason in plain English | AP clerk / purchasing |
| **Insurance** | Each certificate read: insurer, policy, expiry, limit. Red = a problem, yellow = expiring within 30 days, green = OK. | Purchasing / risk |
| **Audit Log** | Every document: what it was read as, the decision and why, the model, tokens and time | Audit / troubleshooting |

### Hold reasons

| Code | Means | Usual next step |
|---|---|---|
| `AMOUNT_OVER_PO` | Total is more than 2% over the PO | Ask purchasing to approve the difference or the vendor for a credit |
| `MISSING_PO` | No PO number printed | Find the PO and ask the vendor to reissue, or have purchasing approve it |
| `PO_NOT_FOUND` | PO number isn't in the PO list | Typo by the vendor, or a PO not entered yet |
| `PO_VENDOR_MISMATCH` | PO belongs to a different vendor | Usually the vendor used the wrong PO |
| `DUPLICATE` | Same vendor and invoice number as one already received | Don't pay; confirm with the vendor if unsure |
| `POSSIBLE_DUPLICATE` | Same vendor, amount and date, different invoice number | Check whether it's a genuine repeat order |
| `MATH_ERROR` | A line, the subtotal, or the total doesn't add up | Ask the vendor for a corrected invoice |
| `COI_MISSING` | On-site contractor with no certificate of insurance | Request one before paying |
| `COI_EXPIRED` | Contractor's insurance has expired | Request the renewal |
| `COI_COVERAGE_LOW` | Per-occurrence limit under $1,000,000 | Request higher coverage, or get an exception approved |
| `UNKNOWN_VENDOR` | Vendor name doesn't match the vendor list | New vendor setup, or a name variation to add |
| `NOT_AN_INVOICE` | Statement, quote, letter, etc. | File it; nothing to pay |
| `UNREADABLE` / `INCOMPLETE` | Claude couldn't read it, or the total/number/vendor is missing | Open the PDF and key it by hand |

Notes (approved, but read them): `WITHIN_TOLERANCE` (over the PO by up to 2%), `COI_EXPIRING` (insurance ends within 30 days).

## Change the rules

All rules live in [`paper_chaser/checks.py`](../paper_chaser/checks.py), at the top:

```python
PO_TOLERANCE = 0.02             # invoice may be up to 2% over its PO
MIN_EACH_OCCURRENCE = 1_000_000 # required general-liability limit for contractors
COI_WARNING_DAYS = 30           # warn when a certificate expires within this many days
```

After any change, run the rule tests (free, about a second) and re-run the batch (free, because reads are saved):

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m paper_chaser.run --as-of 2026-10-14 && .venv/bin/python tests/score.py
```

Which vendors must carry insurance is the `coi_required` column in `data/vendors.csv`. Purchase orders are in `data/purchase_orders.csv`.

## When something goes wrong

| Symptom | Likely cause | Fix |
|---|---|---|
| `No ANTHROPIC_API_KEY found in .env` | Key file missing or in the wrong folder | Re-create `.env` in this folder (see above) |
| A document is held as `UNREADABLE: Claude call failed: AuthenticationError` | Key revoked or mistyped | Make a new key, replace `.env` |
| `UNREADABLE: … RateLimitError` or `OverloadedError` | Too many requests at once | Wait a minute and run again; only the failed files are re-read |
| A genuine invoice shows `UNKNOWN_VENDOR` | Vendor name printed very differently from the vendor list | Fix the name in `data/vendors.csv` |
| The original is held as `DUPLICATE` and the resend approved | File times were reset (copy or clone) | Restore the received order (re-run `make_sample_docs.py` for the test set) |
| `pip install` gives an old `anthropic` 0.x | Python is 3.9 | Use Python 3.10+ |

## Cost

About **2.3¢ per document** with Claude Opus 5.5 (one page is ~4,000 input tokens). A 25-document batch is about $0.60; re-runs from saved reads are free. `--model claude-haiku-5-5` would be far cheaper but hasn't been evaluated on this task.

## Safety and data
- Test data only: every vendor, document and amount here is fictitious.
- The API key stays in `.env`, which is never committed.
- Claude only reads documents. It can't approve, pay, or change any rule; text inside a document is treated as data.
- Every document ends up on a tab: nothing is silently dropped.
