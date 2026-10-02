"""Document extraction service: file → pages → documents → header fields + line items, all as *proposals*.

Flow
  store_file()      keep the original (sha256, never modified)
  run_job()         read each page (native text layer, else OCR), classify, group into documents, read line tables
  review            a person corrects/rejects lines (corrections keep the original: core/overrides.py) and links the
                    document to its PO if it could not be linked automatically
  confirm_document() the reviewed lines become fact_po_line rows linked back to the extracted line, the document and
                    the file page
"""
import hashlib
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.attribution import BranchAttributor
from app.core.exceptions import raise_exception
from app.core.extraction import classify, docx_reader, headers, pdf_native, pdfio
from app.core.extraction import table as tbl
from app.core.extraction.ocr import OcrEngine, OcrPage, default_engine, ocr_page_upright, rotate_image
from app.core.loader_utils import parse_number_year
from app.core.overrides import reapply_approved
from app.core.periods import ensure_period, fiscal_year
from app.models import (
    DocumentFile, ExtractedDocument, ExtractedLine, ExtractedPage, ExtractionJob, FactCost, FactPoLine, PoHeader,
    ProcurementDocument,
)

LINE_BEARING = {"purchase_order", "committee_approval", "payment_request", "supplier_invoice", "quotation", "price_comparison"}
CONFIRMABLE = {"purchase_order"}  # only the PO itself is authoritative for PO lines; memos/invoices are cross-checks
ENVELOPE_TYPES = {"requisition", "quotation", "price_comparison", "committee_approval", "purchase_order", "goods_receipt",
                  "inspection_acceptance", "supplier_invoice", "payment_request"}
MODULE = "purchase_orders"


class ExtractionError(ValueError):
    pass


def store_file(session: Session, filename: str, content: bytes, uploaded_by: str | None = None) -> DocumentFile:
    sha = hashlib.sha256(content).hexdigest()
    existing = session.scalar(select(DocumentFile).where(DocumentFile.sha256 == sha))
    if existing:
        return existing
    ext = Path(filename).suffix.lower()
    folder = Path(get_settings().upload_dir) / "documents"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{sha[:16]}{ext}"
    path.write_bytes(content)
    f = DocumentFile(file_name=Path(filename).name, sha256=sha, storage_path=str(path), uploaded_by=uploaded_by,
                     content_type={".pdf": "application/pdf", ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}.get(ext))
    session.add(f)
    session.commit()
    return f


def create_job(session: Session, filename: str, content: bytes, created_by: str | None = None) -> ExtractionJob:
    ext = Path(filename).suffix.lower()
    if ext not in (".pdf", ".docx"):
        raise ExtractionError(f"Unsupported document type '{ext}'. Supported: .pdf (scanned or native), .docx")
    f = store_file(session, filename, content, created_by)
    job = ExtractionJob(file_id=f.id, status="queued", created_by=created_by, params={"filename": filename})
    session.add(job)
    session.commit()
    return job


@dataclass
class _Page:
    no: int
    text: str
    source: str  # native_text | ocr | docx
    rotation: int = 0
    mean_conf: float = 1.0
    ocr: OcrPage | None = None
    image: Path | None = None  # upright, deskewed page image (scans)
    lines: list = field(default_factory=list)


def _cv_gray(path: Path):
    import cv2
    return cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)


def run_job(session: Session, job_id: int, engine: OcrEngine | None = None, max_pages: int | None = None) -> ExtractionJob:
    job = session.get(ExtractionJob, job_id)
    if job is None:
        raise ExtractionError("job not found")
    job.status, job.started_at = "running", datetime.now(timezone.utc)
    session.commit()
    try:
        f = session.get(DocumentFile, job.file_id)
        path = Path(f.storage_path)
        if path.suffix.lower() == ".docx":
            _run_docx(session, job, f, path)
        else:
            _run_pdf(session, job, f, path, engine or default_engine(), max_pages)
        job.status = "done"
    except Exception as exc:  # noqa: BLE001 - surface any failure on the job, not as a crashed worker
        session.rollback()
        job = session.get(ExtractionJob, job_id)
        job.status, job.error = "failed", f"{type(exc).__name__}: {exc}"[:2000]
    job.finished_at = datetime.now(timezone.utc)
    session.commit()
    return job


# ------------------------------------------------------------------------------------------------ PDF
def _run_pdf(session: Session, job: ExtractionJob, f: DocumentFile, path: Path, engine: OcrEngine, max_pages: int | None) -> None:
    pdfio.require_poppler()
    total = pdfio.page_count(path)
    n = min(total, max_pages) if max_pages else total
    work = Path(get_settings().upload_dir) / "extraction" / f"job_{job.id}"
    work.mkdir(parents=True, exist_ok=True)
    job.page_count = total
    job.engine = engine.name
    job.engine_version = getattr(engine, "version", lambda: None)()
    job.languages = "ara+eng"
    pages: list[_Page] = []
    for p in range(1, n + 1):
        text = pdfio.native_text(path, p)
        if pdfio.has_text_layer(text):
            pg = _Page(p, text, "native_text", lines=headers.lines_from_text(p, text))
        else:
            if not engine.available():
                raise ExtractionError("This PDF is scanned and no OCR engine (tesseract) is available")
            img = pdfio.render_page(path, p, work)
            ocr_pg = ocr_page_upright(engine, img, work)
            upright = img if ocr_pg.rotation == 0 else rotate_image(img, ocr_pg.rotation, work / f"{img.stem}_r{ocr_pg.rotation}.png")
            gray, angle = tbl.deskew(_cv_gray(upright))
            import cv2
            final = work / f"page_{p:03d}.png"
            cv2.imwrite(str(final), gray)
            pg = _Page(p, ocr_pg.text(), "ocr", ocr_pg.rotation, ocr_pg.mean_conf / 100, ocr_pg, final,
                       headers.lines_from_ocr(p, ocr_pg))
        pages.append(pg)
        session.add(ExtractedPage(job_id=job.id, page_no=p, text_source=pg.source, rotation=pg.rotation,
                                  mean_confidence=round(pg.mean_conf, 3), word_count=len(pg.text.split()), raw_text=pg.text,
                                  image_path=str(pg.image) if pg.image else None))
    sources = {pg.source for pg in pages}
    f.source_kind = "pdf_native" if sources == {"native_text"} else ("pdf_scanned" if sources == {"ocr"} else "pdf_mixed")
    f.pages = total
    classes = [classify.classify_text(pg.text) for pg in pages]
    for pg, c in zip(pages, classes):
        row = session.scalar(select(ExtractedPage).where(ExtractedPage.job_id == job.id, ExtractedPage.page_no == pg.no))
        row.doc_type_guess, row.doc_type_confidence = c.doc_type, c.confidence
    session.flush()
    attributor = BranchAttributor(session)
    summary = {"documents": 0, "lines": 0, "types": {}}
    for seq, (dtype, a, b) in enumerate(classify.group_pages(classes), start=1):
        doc_pages = pages[a:b + 1]
        doc = _build_document(session, job, f, seq, dtype, doc_pages, path, engine, attributor,
                              [classes[i].confidence for i in range(a, b + 1)])
        summary["documents"] += 1
        summary["lines"] += session.scalar(select(func.count()).select_from(ExtractedLine).where(ExtractedLine.extracted_document_id == doc.id))
        summary["types"][dtype] = summary["types"].get(dtype, 0) + 1
    job.summary = summary


def _tables_for_page(pg: _Page, path: Path, engine: OcrEngine, work: Path) -> list[tuple[tbl.RawTable, tuple | None]]:
    out = []
    if pg.source == "native_text":
        for t in pdf_native.native_tables(path, pg.no):
            out.append((t, None))
        return out
    gray = _cv_gray(pg.image)
    for g in tbl.detect_grids(gray):
        rt = tbl.read_scanned_table(engine, gray, g, pg.no, work, lang=pg.ocr.lang if pg.ocr else "ara+eng")
        if rt is not None and rt.rows:
            out.append((rt, g.bbox))
    return out


def _stated_total_below(pg: _Page, bbox: tuple) -> tuple[str | None, float | None]:
    """The printed grand total usually sits in the row(s) right under the line table."""
    if pg.ocr is None:
        return None, None
    lines: dict[tuple, list] = {}
    for w in pg.ocr.words:
        if bbox[3] - 20 <= w.cy <= bbox[3] + 700:
            lines.setdefault(w.line_key, []).append(w)
    best = None
    for ws in lines.values():
        text = " ".join(w.text for w in ws)
        if any(k in classify.normalize_text(text) for k in ("الاجمالي", "اجمالي", "total")):
            for w in ws:
                v = tbl.parse_ocr_number(w.text)
                if v is not None and len(w.text.replace(",", "").replace(".", "")) >= 3 and (best is None or v > best[0]):
                    best = (v, w.text, w.conf / 100)
    return (best[1], best[2]) if best else (None, None)


def _build_document(session, job, f, seq, dtype, doc_pages, pdf_path, engine, attributor, page_confs) -> ExtractedDocument:
    lines_all = [ln for pg in doc_pages for ln in pg.lines]
    hdr = headers.extract_po_header(lines_all) if dtype == "purchase_order" else headers.extract_memo_header(lines_all)
    flags: list[str] = []
    scanned = any(pg.source == "ocr" for pg in doc_pages)
    if scanned:
        flags.append("scanned_source_needs_review")
    mean_page_conf = sum(page_confs) / len(page_confs)
    doc = ExtractedDocument(job_id=job.id, seq=seq, doc_type=dtype, page_from=doc_pages[0].no, page_to=doc_pages[-1].no,
                            header=hdr, flags=flags, confidence=round(mean_page_conf, 3))
    session.add(doc)
    session.flush()
    work = Path(get_settings().upload_dir) / "extraction" / f"job_{job.id}"
    parsed_tables: list[tuple[tbl.ParsedTable, tbl.RawTable]] = []
    if dtype in LINE_BEARING:
        for pg in doc_pages:
            for rt, bbox in _tables_for_page(pg, pdf_path, engine, work):
                if bbox is not None and rt.stated_total_raw is None:
                    rt.stated_total_raw, rt.stated_total_conf = _stated_total_below(pg, bbox)
                pt = tbl.lines_from_table(rt)
                if any(l.quantity is not None or l.unit_price is not None or l.line_total is not None for l in pt.lines):
                    parsed_tables.append((pt, rt))
    _persist_lines(session, doc, parsed_tables, attributor)
    _check_document(session, doc, parsed_tables)
    _link_document(session, doc, f)
    return doc


def _persist_lines(session: Session, doc: ExtractedDocument, parsed_tables, attributor: BranchAttributor) -> None:
    n = 0
    for pt, rt in parsed_tables:
        for ln in pt.lines:
            n += 1
            attr = attributor.attribute(ln.description) if ln.description else None
            explicit = attr is not None and attr.status == "auto_assigned"
            session.add(ExtractedLine(
                extracted_document_id=doc.id, line_no=n, page_no=ln.page, bbox=ln.bbox,
                description_raw=ln.description_raw, quantity_raw=ln.quantity_raw, unit_price_raw=ln.unit_price_raw,
                line_total_raw=ln.line_total_raw, description=ln.description, unit_description=ln.unit_description,
                quantity=ln.quantity, unit_price=ln.unit_price, line_total=ln.line_total,
                price_basis=pt.price_basis, field_confidence={k: v for k, v in ln.field_confidence.items() if v is not None},
                confidence=ln.confidence, flags=ln.flags + [f"table:{x}" for x in pt.flags if x.startswith("table_total")],
                branch_source_text=attr.snippet if explicit else None,
                branch_id=attr.branch_id if explicit else None,
                branch_attribution_method=attr.method if explicit else "unallocated_no_explicit_branch",
                branch_attribution_status="auto_assigned" if explicit else "needs_review"))
    session.flush()


def _check_document(session: Session, doc: ExtractedDocument, parsed_tables) -> None:
    flags = list(doc.flags or [])
    if not parsed_tables and doc.doc_type in LINE_BEARING:
        flags.append("no_line_table_found")
    for pt, rt in parsed_tables:
        flags.extend(x for x in pt.flags if x not in flags)
        hdr_total = (doc.header or {}).get("stated_total", {}).get("value")
        if hdr_total and pt.sum_of_lines is not None:
            try:
                if abs(Decimal(str(hdr_total)) - pt.sum_of_lines) > Decimal("1"):
                    flags.append("header_total_differs_from_lines")
            except Exception:  # noqa: BLE001
                pass
        if rt.notes:
            flags.extend(n for n in rt.notes if n not in flags)
    if doc.doc_type == "purchase_order":
        for needed in ("po_number", "po_date", "supplier_name"):
            if needed not in (doc.header or {}):
                flags.append(f"header_missing_{needed}")
    doc.flags = flags


def _link_document(session: Session, doc: ExtractedDocument, f: DocumentFile) -> None:
    hdr = doc.header or {}
    d_str = (hdr.get("po_date") or hdr.get("memo_date") or {}).get("value")
    d = date.fromisoformat(d_str) if d_str else None
    po = None
    if hdr.get("po_number") and d:
        po = session.scalar(select(PoHeader).where(PoHeader.fiscal_year == fiscal_year(d),
                                                  PoHeader.po_number == str(hdr["po_number"]["value"])))
        if po is not None:
            doc.po_header_id, doc.link_method = po.id, "po_number"
    if po is None and hdr.get("requisition_no") and d:
        cands = [h for h in session.scalars(select(PoHeader).where(PoHeader.fiscal_year == fiscal_year(d)))
                 if parse_number_year(h.requisition_no) == (str(hdr["requisition_no"]["value"]), fiscal_year(d))]
        if len(cands) == 1:
            po = cands[0]
            doc.po_header_id, doc.link_method = po.id, "requisition_no"
            doc.flags = [*(doc.flags or []), "linked_by_requisition_only"]
    if po is None and doc.doc_type == "purchase_order":
        doc.flags = [*(doc.flags or []), "po_not_in_register"]
    if po is not None:
        _attach_envelope(session, doc, po)
        if doc.doc_type == "purchase_order" and po.total_amount is not None:
            lines_sum = session.scalar(select(func.sum(ExtractedLine.line_total)).where(
                ExtractedLine.extracted_document_id == doc.id, ExtractedLine.status != "rejected"))
            if lines_sum is not None and abs(Decimal(str(lines_sum)) - Decimal(str(po.total_amount))) > Decimal("1"):
                doc.flags = [*(doc.flags or []), "lines_total_differs_from_register"]
                raise_exception(session, "extraction_total_differs_register", "warning", "po_header", f"{po.fiscal_year}/{po.po_number}",
                                "Sum of the extracted PO lines differs from the total in the PO register",
                                {"lines_total": str(lines_sum), "register_total": str(po.total_amount), "extracted_document_id": doc.id},
                                MODULE)
    elif doc.doc_type == "purchase_order":
        raise_exception(session, "extraction_po_not_in_register", "warning", "extracted_document", str(doc.id),
                        "A PO document was read but no matching PO exists in the register (link it manually or load the register)",
                        {"po_number": (hdr.get("po_number") or {}).get("value"), "po_date": d_str}, MODULE)


def _attach_envelope(session: Session, doc: ExtractedDocument, po: PoHeader) -> None:
    """Register the document in the procurement document graph, pointing at its file and pages."""
    if doc.procurement_document_id or doc.doc_type not in ENVELOPE_TYPES:
        return
    hdr = doc.header or {}
    d_str = (hdr.get("po_date") or hdr.get("memo_date") or {}).get("value")
    job = session.get(ExtractionJob, doc.job_id)
    env = ProcurementDocument(case_id=po.case_id, po_header_id=po.id, doc_type=doc.doc_type,
                              doc_number=str((hdr.get("po_number") or {}).get("value") or ""),
                              doc_date=date.fromisoformat(d_str) if d_str else None, fiscal_year=po.fiscal_year,
                              supplier_id=po.supplier_id, file_id=job.file_id, page_from=doc.page_from, page_to=doc.page_to,
                              status="extracted_pending_review", attrs={"extracted_document_id": doc.id})
    session.add(env)
    session.flush()
    doc.procurement_document_id = env.id


# ------------------------------------------------------------------------------------------------ Word
def _run_docx(session: Session, job: ExtractionJob, f: DocumentFile, path: Path) -> None:
    memos = docx_reader.read_docx(path)
    f.source_kind = "docx"
    job.engine, job.languages, job.page_count = "docx-native", None, len(memos)
    attributor = BranchAttributor(session)
    summary = {"documents": 0, "lines": 0, "types": {}}
    for m in memos:
        c = classify.classify_text(m.text)
        dtype = c.doc_type if c.doc_type != "purchase_order_terms" else "unknown"
        session.add(ExtractedPage(job_id=job.id, page_no=m.seq, text_source="docx", mean_confidence=1.0,
                                  word_count=len(m.text.split()), raw_text=m.text, doc_type_guess=dtype,
                                  doc_type_confidence=c.confidence))
        hdr = headers.extract_memo_header(m.lines)
        doc = ExtractedDocument(job_id=job.id, seq=m.seq, doc_type=dtype, page_from=m.seq, page_to=m.seq, header=hdr,
                                flags=[], confidence=c.confidence)
        session.add(doc)
        session.flush()
        parsed = []
        for rt in m.tables:
            pt = tbl.lines_from_table(rt)
            if pt.lines:
                parsed.append((pt, rt))
        _persist_lines(session, doc, parsed, attributor)
        _check_document(session, doc, parsed)
        if c.confidence < 0.6:
            doc.flags = [*(doc.flags or []), "document_type_uncertain"]
        _link_document(session, doc, f)
        summary["documents"] += 1
        summary["lines"] += sum(len(pt.lines) for pt, _ in parsed)
        summary["types"][dtype] = summary["types"].get(dtype, 0) + 1
    job.summary = summary


# ------------------------------------------------------------------------------------------------ review / confirm
def link_document(session: Session, doc_id: int, fiscal_year_: int, po_number: str, user: str) -> ExtractedDocument:
    doc = session.get(ExtractedDocument, doc_id)
    if doc is None:
        raise ExtractionError("document not found")
    po = session.scalar(select(PoHeader).where(PoHeader.fiscal_year == fiscal_year_, PoHeader.po_number == str(po_number)))
    if po is None:
        raise ExtractionError(f"PO {fiscal_year_}/{po_number} not found")
    doc.po_header_id, doc.link_method = po.id, "manual"
    doc.flags = [f for f in (doc.flags or []) if f not in ("po_not_in_register", "linked_by_requisition_only")]
    _attach_envelope(session, doc, po)
    doc.reviewed_by = user
    session.commit()
    return doc


def reject_document(session: Session, doc_id: int, user: str, note: str | None = None) -> ExtractedDocument:
    doc = session.get(ExtractedDocument, doc_id)
    if doc is None:
        raise ExtractionError("document not found")
    if doc.status == "confirmed":
        raise ExtractionError("A confirmed document cannot be rejected; revert its PO lines first")
    doc.status, doc.reviewed_by, doc.reviewed_at, doc.review_note = "rejected", user, datetime.now(timezone.utc), note
    session.commit()
    return doc


def set_line_status(session: Session, line_id: int, status: str) -> ExtractedLine:
    if status not in ("extracted", "rejected", "reviewed"):
        raise ExtractionError("status must be 'rejected', 'extracted' (restore) or 'reviewed' (a person accepts the row, "
                              "e.g. an adjustment row that should be kept)")
    line = session.get(ExtractedLine, line_id)
    if line is None:
        raise ExtractionError("line not found")
    if line.status == "confirmed":
        raise ExtractionError("A confirmed line cannot be changed here")
    line.status = status
    session.commit()
    return line


def confirm_document(session: Session, doc_id: int, user: str, replace: bool = False) -> list[FactPoLine]:
    """Turn reviewed lines of a PO document into PO lines. Refuses while any kept line is incomplete: unreadable
    values are corrected (with a recorded reason) or the line is rejected - never silently guessed."""
    doc = session.get(ExtractedDocument, doc_id)
    if doc is None:
        raise ExtractionError("document not found")
    if doc.doc_type not in CONFIRMABLE:
        raise ExtractionError(f"Only {sorted(CONFIRMABLE)} documents can be confirmed into PO lines (this is '{doc.doc_type}')")
    if doc.status == "rejected":
        raise ExtractionError("This document was rejected")
    if doc.po_header_id is None:
        raise ExtractionError("Link the document to a PO first")
    header = session.get(PoHeader, doc.po_header_id)
    lines = list(session.scalars(select(ExtractedLine).where(
        ExtractedLine.extracted_document_id == doc.id, ExtractedLine.status != "rejected").order_by(ExtractedLine.line_no)))
    kept = [ln for ln in lines if "adjustment_row" not in (ln.flags or []) or ln.status == "reviewed"]
    if not kept:
        raise ExtractionError("No lines to confirm")
    incomplete = [ln.line_no for ln in kept if ln.quantity is None or ln.unit_price is None or ln.line_total is None
                  or not (ln.description or "").strip()]
    if incomplete:
        raise ExtractionError(f"Lines {incomplete} are incomplete: correct them (with a reason) or reject them first")
    other = session.scalar(select(func.count()).select_from(FactPoLine).where(
        FactPoLine.po_header_id == header.id, FactPoLine.source_kind == "document_extraction",
        FactPoLine.extracted_line_id.not_in(select(ExtractedLine.id).where(ExtractedLine.extracted_document_id == doc.id))))
    if other and not replace:
        raise ExtractionError("This PO already has lines from another document: pass replace=true to supersede them")
    if replace:
        for old in session.scalars(select(FactPoLine).where(FactPoLine.po_header_id == header.id)):
            session.execute(FactCost.__table__.delete().where(FactCost.source_ref == f"po_line:{old.id}"))
            session.delete(old)
        session.flush()
    d = header.po_date
    if d is None:
        hd = (doc.header or {}).get("po_date", {}).get("value")
        d = date.fromisoformat(hd) if hd else None
    period = ensure_period(session, d) if d else header.period
    out: list[FactPoLine] = []
    for ln in kept:
        existing = session.scalar(select(FactPoLine).where(FactPoLine.po_header_id == header.id,
                                                           FactPoLine.line_number == ln.line_no))
        row = existing or FactPoLine(po_header_id=header.id, line_number=ln.line_no)
        if existing is None:
            session.add(row)
        row.fiscal_year, row.po_number, row.po_date = header.fiscal_year, header.po_number, d or header.po_date
        row.period = period
        row.supplier_id = header.supplier_id
        row.item_description = ln.description
        row.uom = ln.unit_description[:20] if ln.unit_description else None
        row.quantity, row.unit_price, row.line_amount = ln.quantity, ln.unit_price, ln.line_total
        row.currency = header.currency
        row.price_basis = ln.price_basis
        row.source_kind, row.extracted_line_id = "document_extraction", ln.id
        # branch: this line's own explicit text, else the PO's confirmed/explicit attribution, else Unallocated
        if ln.branch_attribution_status == "auto_assigned":
            row.branch_id, row.branch_attribution_method, row.branch_attribution_status = ln.branch_id, ln.branch_attribution_method, "auto_assigned"
            row.branch_source_text = ln.branch_source_text
        else:
            row.branch_id = header.branch_id
            row.branch_attribution_method = f"inherited_from_po:{header.branch_attribution_method}"
            row.branch_attribution_status = header.branch_attribution_status or "needs_review"
            row.branch_source_text = header.branch_source_text
        session.flush()
        reapply_approved(session, "po_line", f"{header.fiscal_year}/{header.po_number}#{ln.line_no}", row)
        cost = session.scalar(select(FactCost).where(FactCost.module_id == MODULE, FactCost.source_ref == f"po_line:{row.id}"))
        if cost is None:
            cost = FactCost(module_id=MODULE, source_ref=f"po_line:{row.id}")
            session.add(cost)
        cost.period, cost.branch_id, cost.supplier_id = row.period, row.branch_id, row.supplier_id
        cost.cost_center_id, cost.amount, cost.currency = header.cost_center_id, row.line_amount, row.currency
        cost.attrs = {"po_number": header.po_number, "fiscal_year": header.fiscal_year, "line_number": ln.line_no,
                      "source": "document_extraction"}
        ln.po_line_id, ln.status = row.id, "confirmed"
        out.append(row)
    session.flush()
    header.lines_total = session.scalar(select(func.sum(FactPoLine.line_amount)).where(FactPoLine.po_header_id == header.id))
    header.granularity = "lines"
    old_cost = session.scalar(select(FactCost).where(FactCost.module_id == MODULE, FactCost.source_ref == f"po:{header.id}"))
    if old_cost is not None:
        session.delete(old_cost)  # line-level cost rows now carry the spend
    if header.total_amount is not None and abs(Decimal(str(header.lines_total)) - Decimal(str(header.total_amount))) > Decimal("1"):
        raise_exception(session, "po_lines_total_differs_register", "warning", "po_header", f"{header.fiscal_year}/{header.po_number}",
                        "The confirmed PO lines add up to a different amount than the register's PO total (the register total "
                        "is kept as the stated value)", {"lines_total": str(header.lines_total), "register_total": str(header.total_amount)},
                        MODULE)
    doc.status, doc.reviewed_by, doc.reviewed_at = "confirmed", user, datetime.now(timezone.utc)
    if doc.procurement_document_id:
        env = session.get(ProcurementDocument, doc.procurement_document_id)
        if env:
            env.status = "confirmed"
    session.commit()
    return out


def cross_check(session: Session, po_header_id: int) -> dict:
    """Do the other documents of a PO (committee memo, payment memo, invoice, quotation) agree with the PO document?

    Compares totals and matches lines by (quantity, amount). Differences are reported, never resolved: the PO document
    stays the reference and the people involved decide.
    """
    docs = list(session.scalars(select(ExtractedDocument).where(
        ExtractedDocument.po_header_id == po_header_id, ExtractedDocument.status != "rejected").order_by(ExtractedDocument.id)))

    def items(d: ExtractedDocument) -> list[ExtractedLine]:
        return [ln for ln in session.scalars(select(ExtractedLine).where(
            ExtractedLine.extracted_document_id == d.id, ExtractedLine.status != "rejected").order_by(ExtractedLine.line_no))
            if "adjustment_row" not in (ln.flags or [])]

    def key(ln: ExtractedLine):
        return (None if ln.quantity is None else Decimal(str(ln.quantity)).normalize(),
                None if ln.line_total is None else Decimal(str(ln.line_total)).quantize(Decimal("0.01")))

    ref = next((d for d in docs if d.doc_type == "purchase_order" and session.scalar(
        select(func.count()).select_from(ExtractedLine).where(ExtractedLine.extracted_document_id == d.id))), None)
    header = session.get(PoHeader, po_header_id)
    out: dict = {"po": f"{header.fiscal_year}/{header.po_number}" if header else None,
                 "register_total": None if header is None or header.total_amount is None else float(header.total_amount),
                 "reference_document_id": ref.id if ref else None, "documents": []}
    if ref is None:
        out["note"] = "No PO document with lines is linked yet"
        return out
    ref_lines = items(ref)
    ref_total = sum((Decimal(str(ln.line_total)) for ln in ref_lines if ln.line_total is not None), Decimal(0))
    out["reference_total"] = float(ref_total)
    if header is not None and header.total_amount is not None:
        out["reference_matches_register"] = abs(ref_total - Decimal(str(header.total_amount))) <= Decimal("1")
    for d in docs:
        if d.id == ref.id:
            continue
        lines = items(d)
        total = sum((Decimal(str(ln.line_total)) for ln in lines if ln.line_total is not None), Decimal(0))
        stated = (d.header or {}).get("stated_total", {}).get("value")
        ref_keys, other_keys = [key(ln) for ln in ref_lines], [key(ln) for ln in lines]
        remaining = list(ref_keys)
        matched = 0
        only_here = []
        for k, ln in zip(other_keys, lines):
            if k in remaining:
                remaining.remove(k)
                matched += 1
            else:
                only_here.append({"line_no": ln.line_no, "description": ln.description, "quantity": k[0] and float(k[0]), "amount": k[1] and float(k[1])})
        out["documents"].append({
            "document_id": d.id, "doc_type": d.doc_type, "lines": len(lines), "lines_total": float(total),
            "stated_total": None if stated is None else float(stated),
            "total_matches_po": bool(lines) and abs(total - ref_total) <= Decimal("1"),
            "lines_matched_to_po": matched, "lines_only_in_this_document": only_here,
            "po_lines_missing_here": [{"quantity": k[0] and float(k[0]), "amount": k[1] and float(k[1])} for k in remaining],
            "price_basis": next((ln.price_basis for ln in lines if ln.price_basis), None)})
    return out
