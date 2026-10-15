# Sample output: what Paper Chaser produces

A Markdown copy of [`sample-output.xlsx`](sample-output.xlsx) ([download the Excel file](https://github.com/NormStormm/paper-chaser/raw/main/docs/sample-output.xlsx)), from one run on the 25 test documents. In Excel, held rows are red, notes yellow, and good insurance green.

## Summary

| | |
|---|---|
| Run on | 2026-10-14 22:35 |
| Checked as of | 2026-10-14 |
| Model | claude-opus-5-5 |
| Documents read | 25 |
| Invoices approved to enter | 10 |
|   Amount approved | $14,241.41 |
| On hold for review | 11 |
|   Invoice amount on hold | $17,594.12 |
| Insurance certificates recorded | 4 |
| Approved with a note to read | 2 |
| Every amount and status comes from plain-code checks. Claude only reads the documents. |  |

## Approved

| File | Vendor | Invoice # | Invoice date | Due date | PO # | Total | Note |
|---|---|---|---|---|---|---|---|
| Invoice_KLS-10233.pdf | Kapena Linen Service | KLS-10233 | 2026-10-01 | 2026-10-31 | PO-24101 | $1,691.10 |  |
| EPP-5571.pdf | Ewa Plains Produce Co. | EPP-5571 | 2026-10-03 | 2026-11-02 | PO-24102 | $1,194.50 |  |
| koolau_inv_0918.pdf | Koolau Coffee Roasters | KCR-0918 | 2026-10-02 | 2026-11-01 | PO-24103 | $1,938.22 |  |
| PPC-2026-114.pdf | Pueo Pest Control LLC | PPC-2026-114 | 2026-10-06 | 2026-11-05 | PO-24104 | $1,916.23 |  |
| KPJ-77812.pdf | Kalo Paper & Janitorial Supply | KPJ-77812 | 2026-10-05 | 2026-11-04 | PO-24105 | $1,913.51 | 1.5% over PO ($1,913.51 vs $1,885.23), within the 2% limit |
| LLE-2207.pdf | Leeward Line Electric | LLE-2207 | 2026-10-08 | 2026-11-07 | PO-24109 | $1,830.37 | Insurance expires in 12 days (Oct 26, 2026): request a renewal |
| scan_0042.pdf | Makai Fish Market Wholesale | MFW-3315 | 2026-10-11 |  | PO-24112 | $913.61 |  |
| HPW-1192.pdf | Hale Print Works | HPW-1192 | 2026-10-10 | 2026-11-09 | PO-24114 | $1,005.55 |  |
| KCR-0940.pdf | Koolau Coffee Roasters | KCR-0940 | 2026-10-12 | 2026-11-11 | PO-24116 | $1,272.88 |  |
| PPC-2026-121.pdf | Pueo Pest Control LLC | PPC-2026-121 | 2026-10-12 | 2026-11-11 | PO-24117 | $565.44 |  |

## Exceptions

| File | Type | Vendor | Invoice # | PO # | Total | Why it's on hold | Reason codes |
|---|---|---|---|---|---|---|---|
| MFW-3301.pdf | INVOICE | Makai Fish Market Wholesale | MFW-3301 | PO-24106 | $1,941.62 | Amount $1,941.62 vs PO $1,790.00 (+8.5%, limit 2%) | AMOUNT_OVER_PO |
| HPW-1188.pdf | INVOICE | Hale Print Works | HPW-1188 |  | $1,078.53 | No PO number on the invoice | MISSING_PO |
| EPP-5590.pdf | INVOICE | Ewa Plains Produce Co. | EPP-5590 | PO-29999 | $608.64 | PO PO-29999 doesn't exist | PO_NOT_FOUND |
| FW_ Invoice KLS-10233 (resend).pdf | INVOICE | Kapena Linen Service | KLS-10233 | PO-24101 | $1,691.10 | Duplicate of Invoice_KLS-10233.pdf (same invoice number KLS-10233) | DUPLICATE |
| KCR-0931.pdf | INVOICE | Koolau Coffee Roasters | KCR-0931 | PO-24107 | $1,729.58 | Amount $1,729.58 vs PO $1,679.58 (+3.0%, limit 2%)<br>Invoice doesn't add up: subtotal - discount + tax = $1,679.58, total says $1,729.58 | AMOUNT_OVER_PO, MATH_ERROR |
| MAR-4410.pdf | INVOICE | Mauka Air & Refrigeration | MAR-4410 | PO-24108 | $3,565.44 | Insurance expired Sep 30, 2026 (14 days ago) | COI_EXPIRED |
| LPS-0612.pdf | INVOICE | Lanikai Pool Services | LPS-0612 | PO-24110 | $1,513.09 | Insurance limit $500,000.00 per occurrence is below the required $1,000,000.00 | COI_COVERAGE_LOW |
| NL-3005.pdf | INVOICE | Nalu Landscaping | NL-3005 | PO-24111 | $3,790.57 | Contractor has no certificate of insurance on file | COI_MISSING |
| KPJ-77830.pdf | INVOICE | Kalo Paper & Janitorial Supply | KPJ-77830 | PO-24113 | $481.05 | PO PO-24113 belongs to Hale Print Works, not Kalo Paper & Janitorial Supply | PO_VENDOR_MISMATCH |
| Ewa Plains invoice.pdf | INVOICE | Ewa Plains Produce Co. | EPP-5594 | PO-24115 | $1,194.50 | Possible duplicate of EPP-5571.pdf (same vendor, amount $1,194.50 and date, different invoice number) | POSSIBLE_DUPLICATE |
| Kapena_statement_Sept.pdf | OTHER | Kapena Linen Service |  |  |  | Not an invoice (e.g. a statement or letter); nothing to pay | NOT_AN_INVOICE |

## Insurance

| File | Insured vendor | Insurer | Policy # | Expires | Per occurrence | Status |
|---|---|---|---|---|---|---|
| COI_PueoPest_2026.pdf | Pueo Pest Control LLC | Fictional Mutual Insurance Co. | GL-PPC-882341 | 2027-03-31 | $1,000,000.00 | OK |
| scan_0051.pdf | Mauka Air & Refrigeration | Example Casualty Group | CGL-55190-MA | 2026-09-30 | $2,000,000.00 | Insurance expired Sep 30, 2026 (14 days ago) |
| LeewardLine_COI.pdf | Leeward Line Electric | Sample Indemnity Ltd. | LL-10992-E | 2026-10-26 | $1,000,000.00 | Insurance expires in 12 days (Oct 26, 2026): request a renewal |
| Lanikai Pool - certificate of insurance.pdf | Lanikai Pool Services | Fictional Mutual Insurance Co. | GL-LPS-30117 | 2027-05-01 | $500,000.00 | Insurance limit $500,000.00 per occurrence is below the required $1,000,000.00 |

## Audit Log

| File | Read as | Decision | Details |
|---|---|---|---|
| COI_PueoPest_2026.pdf | COI | RECORDED | Recorded |
| scan_0051.pdf | COI | RECORDED | Insurance expired Sep 30, 2026 (14 days ago) |
| LeewardLine_COI.pdf | COI | RECORDED | Insurance expires in 12 days (Oct 26, 2026): request a renewal |
| Lanikai Pool - certificate of insurance.pdf | COI | RECORDED | Insurance limit $500,000.00 per occurrence is below the required $1,000,000.00 |
| Invoice_KLS-10233.pdf | INVOICE | APPROVED | All checks passed  [Claude: Document is marked as a sample with a fictitious vendor created for software testing.] |
| EPP-5571.pdf | INVOICE | APPROVED | All checks passed |
| koolau_inv_0918.pdf | INVOICE | APPROVED | All checks passed  [Claude: Invoice date printed as 10/02/2026 was read as October 2, 2026, consistent with Net 30 terms and the printed due date of 2026-11-01.] |
| PPC-2026-114.pdf | INVOICE | APPROVED | All checks passed |
| KPJ-77812.pdf | INVOICE | APPROVED | 1.5% over PO ($1,913.51 vs $1,885.23), within the 2% limit |
| MFW-3301.pdf | INVOICE | HOLD | Amount $1,941.62 vs PO $1,790.00 (+8.5%, limit 2%)  [Claude: Invoice date is printed as 10/07/2026 and was read as October 7 (MM/DD), which matches the Net 30 due date of 2026-11-06.] |
| HPW-1188.pdf | INVOICE | HOLD | No PO number on the invoice |
| EPP-5590.pdf | INVOICE | HOLD | PO PO-29999 doesn't exist |
| FW_ Invoice KLS-10233 (resend).pdf | INVOICE | HOLD | Duplicate of Invoice_KLS-10233.pdf (same invoice number KLS-10233)  [Claude: The document is labeled as a sample from a fictitious vendor created for software testing.] |
| KCR-0931.pdf | INVOICE | HOLD | Amount $1,729.58 vs PO $1,679.58 (+3.0%, limit 2%); Invoice doesn't add up: subtotal - discount + tax = $1,679.58, total says $1,729.58  [Claude: The printed total of 1729.58 does not equal subtotal plus GET (1679.58), a 50.00 difference.] |
| MAR-4410.pdf | INVOICE | HOLD | Insurance expired Sep 30, 2026 (14 days ago) |
| LLE-2207.pdf | INVOICE | APPROVED | Insurance expires in 12 days (Oct 26, 2026): request a renewal |
| LPS-0612.pdf | INVOICE | HOLD | Insurance limit $500,000.00 per occurrence is below the required $1,000,000.00 |
| NL-3005.pdf | INVOICE | HOLD | Contractor has no certificate of insurance on file |
| scan_0042.pdf | INVOICE | APPROVED | All checks passed |
| KPJ-77830.pdf | INVOICE | HOLD | PO PO-24113 belongs to Hale Print Works, not Kalo Paper & Janitorial Supply |
| HPW-1192.pdf | INVOICE | APPROVED | All checks passed  [Claude: Document is marked as a sample with a fictitious vendor created for software testing.] |
| Ewa Plains invoice.pdf | INVOICE | HOLD | Possible duplicate of EPP-5571.pdf (same vendor, amount $1,194.50 and date, different invoice number)  [Claude: Document footer marks it as a sample with a fictitious vendor created for software testing.] |
| KCR-0940.pdf | INVOICE | APPROVED | All checks passed  [Claude: Invoice date is printed as 10/12/2026 and was read as October 12, which matches the Net 30 due date of 2026-11-11.] |
| PPC-2026-121.pdf | INVOICE | APPROVED | All checks passed |
| Kapena_statement_Sept.pdf | OTHER | HOLD | Not an invoice (e.g. a statement or letter); nothing to pay  [Claude: This is a statement of account for September 2026, not an invoice; it lists invoices KLS-10107 and KLS-10170 as paid and shows an account balance of $0.00.] |

*All vendors, documents and amounts are fictitious test data.*
