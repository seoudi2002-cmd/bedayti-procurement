# Document intake — how new Excel / Word / PDF files enter the platform

Goal: give the platform a report file or transaction documents and have it **read → validate → identify the module →
clean/map → detect duplicates & anomalies → calculate KPIs → analyse → report**, without redesigning anything per file.

```
file ──► reader (by extension) ──► TableData ──► module/profile detection ──► mapping ──► validation ──► loader ──► facts
 xlsx/csv   Word/PDF extractor ──┘   (same shape)   POST /api/intake/analyze     (aliases)  (clean/flag)   (+exceptions)
```

## Works today (Excel / CSV)
- `POST /api/intake/analyze` scores every sheet against every module/profile by header coverage (required fields weigh most, the expected sheet name is a small bonus) and returns a recommendation, or **none** when nothing fits (never forced).
- `POST /api/imports` (module, profile, sheet) → stage; `…/validate` → clean, flag, skip subtotal rows, fill merged cells; `…/load` → loader; every step is auditable (`raw_row`, `validation_issue`, `data_exception`, `column_map` stored per batch).
- Duplicates: identical file hash is refused; natural-key upserts (PO number, memo number, supplier code …); conflicting keys are held + flagged; possible duplicate memos are flagged.
- Anomalies today are rule-coded in each loader (invalid dates, handover > total, supplier name mismatch, …). A declarative rule layer (`rules.yaml`) and statistical anomaly detection come with the insight engine.

## Plug-in point for Word / PDF
Readers are registered by extension in `core/ingestion/readers.py` (`register_reader`). A Word/PDF extractor must return a
`TableData` whose headers are canonical field names (or aliases) — then **everything downstream is shared**:
detection, mapping, validation, upsert, exceptions, KPIs. Extraction output is *suggested data*:
1. **Text layer first** (Word, digital PDFs, e-invoices have clean text/QR data); **OCR** for scans (Arabic print is workable; handwriting, stamps and signatures are not reliable).
2. Each extracted field carries its **source snippet, page and a confidence**; low-confidence or missing fields are left empty, never filled.
3. A person **confirms** extracted documents in a review screen before they are loaded (human-in-the-loop); confirmed values go through the normal validation.
4. The original file is stored (`document_file`, sha256) and linked to the case (`procurement_document`), so every number traces to a page.

### Proposed document types (from the sample transaction)
requisition · quotation · price comparison · committee approval · **PO (lines: item, qty, unit price, total, terms)** · goods receipt · inspection & acceptance · supplier invoice (e-invoice id, tax IDs, lines) · payment/transfer request · bank transfer confirmation. Each becomes a document type in `module.yaml` with a field list; the PO extractor feeds the **line-level profile** that already exists.

### What I need to build the first extractor
5–10 sanitised PO PDFs/Word files (mixed quality, incl. a scan), the matching committee/quotation documents for 2–3 of them,
and for each: which fields you want captured. Start with POs (they unlock line prices, quantities, delivery/payment terms and unit-price analysis).
