# Reference samples under investigation (NOT loaded)

## Branch workbook › sheet `الفروع الجديدة`
Status: **investigation only**. It is not loaded into the branch master and feeds nothing, until its business purpose is confirmed.

Observed structure (values omitted):
- 12 data rows, each naming an **existing** branch from the master (so it is not a list of new branches) with its region, region manager, address, branch manager and phones.
- The last column carries a short note per branch: **"3 ورق طباعة"** on 10 rows and **"3000 ورق دعايا"** on 2 rows (quantity + item: printing paper / promotional paper).
- The headers of columns I–J read `مبرد` (water cooler) and `كاتل` (kettle), but those columns contain phone numbers (I) and the paper notes (J): **the header labels do not describe the content**, which suggests the sheet was reused from an earlier distribution list.
- Above the data: leftover per-region subtotal lines (one with `#REF!`) and blank rows.
- Regions covered: 8; per region 1–2 branches.

What it most likely is (hypothesis, unconfirmed): a one-off **supply distribution/allocation list** (paper, promotional paper) to selected branches.
If confirmed it belongs to the **Paper consumption** module as an *allocation* source (branch, item, quantity, date/reference), and could also supply explicit branch allocation for the paper PO (whose documents say "head office and company branches").

Questions to answer before any load: what does "3" mean (cartons? reams? per branch per month?), which PO/delivery does it belong to, why only these 12 branches, is there a date, and are there other versions of this list?

## Branch workbook › sheet `Sheet1`
A scratch branch → governorate list (96 of 100 branches) with a few personal contact notes. Not used (the master already carries the region). Its governorate column could be used later as a cross-check of the region assignment.
