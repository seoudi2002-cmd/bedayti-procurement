"""Document extraction API. Everything here works on proposals: nothing becomes a PO line until confirmed."""
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.auth import Principal, require
from app.core.extraction import service
from app.core.overrides import history
from app.db import get_engine, get_session
from app.models import ExtractedDocument, ExtractedLine, ExtractedPage, ExtractionJob

router = APIRouter(prefix="/extraction")


def _run_in_background(job_id: int) -> None:
    with Session(get_engine()) as session:
        service.run_job(session, job_id)


def _line_json(session: Session, ln: ExtractedLine) -> dict:
    return {
        "id": ln.id, "line_no": ln.line_no, "page": ln.page_no, "bbox": ln.bbox, "status": ln.status,
        "as_read": {"description": ln.description_raw, "quantity": ln.quantity_raw, "unit_price": ln.unit_price_raw,
                    "line_total": ln.line_total_raw},
        "parsed": {"description": ln.description, "unit": ln.unit_description,
                   "quantity": None if ln.quantity is None else float(ln.quantity),
                   "unit_price": None if ln.unit_price is None else float(ln.unit_price),
                   "line_total": None if ln.line_total is None else float(ln.line_total), "price_basis": ln.price_basis},
        "confidence": None if ln.confidence is None else float(ln.confidence), "field_confidence": ln.field_confidence,
        "flags": ln.flags,
        "branch": {"id": ln.branch_id, "method": ln.branch_attribution_method, "status": ln.branch_attribution_status,
                   "source_text": ln.branch_source_text},
        "corrections": [{"id": o.id, "field": o.field, "original_value": o.original_value,
                         "corrected_value": o.corrected_value, "reason": o.reason, "status": o.status,
                         "proposed_by": o.proposed_by, "reviewed_by": o.reviewed_by}
                        for o in history(session, "extracted_line", str(ln.id))],
        "po_line_id": ln.po_line_id,
    }


def _doc_json(session: Session, doc: ExtractedDocument, with_lines: bool = False) -> dict:
    n = session.scalar(select(func.count()).select_from(ExtractedLine).where(ExtractedLine.extracted_document_id == doc.id))
    out = {"id": doc.id, "job_id": doc.job_id, "seq": doc.seq, "doc_type": doc.doc_type, "pages": [doc.page_from, doc.page_to],
           "status": doc.status, "confidence": None if doc.confidence is None else float(doc.confidence),
           "header": doc.header, "flags": doc.flags, "lines": n, "po_header_id": doc.po_header_id, "link_method": doc.link_method,
           "reviewed_by": doc.reviewed_by, "review_note": doc.review_note}
    if with_lines:
        out["line_items"] = [_line_json(session, ln) for ln in session.scalars(
            select(ExtractedLine).where(ExtractedLine.extracted_document_id == doc.id).order_by(ExtractedLine.line_no))]
    return out


@router.post("/jobs", status_code=202)
async def create_job(background: BackgroundTasks, file: UploadFile = File(...), wait: bool = False,
                     session: Session = Depends(get_session), principal: Principal = Depends(require("analyst"))):
    content = await file.read()
    if len(content) > get_settings().max_upload_mb * 1024 * 1024:
        raise HTTPException(413, "File too large")
    try:
        job = service.create_job(session, file.filename or "upload", content, principal.name)
    except service.ExtractionError as exc:
        raise HTTPException(415, str(exc)) from exc
    if wait:
        job = service.run_job(session, job.id)
    else:
        background.add_task(_run_in_background, job.id)
    return {"job_id": job.id, "status": job.status}


@router.get("/jobs")
def list_jobs(session: Session = Depends(get_session), _: Principal = Depends(require("analyst"))):
    return [{"id": j.id, "file_id": j.file_id, "status": j.status, "pages": j.page_count, "summary": j.summary,
             "created_by": j.created_by, "created_at": j.created_at}
            for j in session.scalars(select(ExtractionJob).order_by(ExtractionJob.id.desc()).limit(100))]


@router.get("/jobs/{job_id}")
def get_job(job_id: int, session: Session = Depends(get_session), _: Principal = Depends(require("analyst"))):
    job = session.get(ExtractionJob, job_id)
    if job is None:
        raise HTTPException(404, "Job not found")
    docs = session.scalars(select(ExtractedDocument).where(ExtractedDocument.job_id == job_id).order_by(ExtractedDocument.seq))
    return {"id": job.id, "status": job.status, "error": job.error, "engine": job.engine, "engine_version": job.engine_version,
            "languages": job.languages, "pages": job.page_count, "summary": job.summary,
            "documents": [_doc_json(session, d) for d in docs]}


@router.get("/documents/{doc_id}")
def get_document(doc_id: int, session: Session = Depends(get_session), _: Principal = Depends(require("analyst"))):
    doc = session.get(ExtractedDocument, doc_id)
    if doc is None:
        raise HTTPException(404, "Document not found")
    return _doc_json(session, doc, with_lines=True)


@router.get("/jobs/{job_id}/pages/{page_no}")
def get_page(job_id: int, page_no: int, session: Session = Depends(get_session), _: Principal = Depends(require("analyst"))):
    page = session.scalar(select(ExtractedPage).where(ExtractedPage.job_id == job_id, ExtractedPage.page_no == page_no))
    if page is None:
        raise HTTPException(404, "Page not found")
    return {"page": page.page_no, "source": page.text_source, "rotation": page.rotation,
            "mean_confidence": None if page.mean_confidence is None else float(page.mean_confidence),
            "doc_type_guess": page.doc_type_guess, "doc_type_confidence": None if page.doc_type_confidence is None else float(page.doc_type_confidence),
            "text": page.raw_text, "has_image": bool(page.image_path)}


@router.get("/jobs/{job_id}/pages/{page_no}/image")
def get_page_image(job_id: int, page_no: int, session: Session = Depends(get_session),
                   _: Principal = Depends(require("analyst"))):
    page = session.scalar(select(ExtractedPage).where(ExtractedPage.job_id == job_id, ExtractedPage.page_no == page_no))
    if page is None or not page.image_path or not Path(page.image_path).exists():
        raise HTTPException(404, "No image for this page")
    return FileResponse(page.image_path, media_type="image/png")


class LinkIn(BaseModel):
    fiscal_year: int
    po_number: str


class ConfirmIn(BaseModel):
    replace: bool = False


class NoteIn(BaseModel):
    note: str | None = None


class LineStatusIn(BaseModel):
    status: str  # rejected | extracted | reviewed


def _svc(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except service.ExtractionError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post("/documents/{doc_id}/link")
def link(doc_id: int, body: LinkIn, session: Session = Depends(get_session), principal: Principal = Depends(require("analyst"))):
    return _doc_json(session, _svc(service.link_document, session, doc_id, body.fiscal_year, body.po_number, principal.name))


@router.post("/documents/{doc_id}/confirm")
def confirm(doc_id: int, body: ConfirmIn, session: Session = Depends(get_session), principal: Principal = Depends(require("analyst"))):
    rows = _svc(service.confirm_document, session, doc_id, principal.name, body.replace)
    return {"document_id": doc_id, "po_lines_written": len(rows)}


@router.post("/documents/{doc_id}/reject")
def reject(doc_id: int, body: NoteIn, session: Session = Depends(get_session), principal: Principal = Depends(require("analyst"))):
    return _doc_json(session, _svc(service.reject_document, session, doc_id, principal.name, body.note))


@router.post("/lines/{line_id}/status")
def line_status(line_id: int, body: LineStatusIn, session: Session = Depends(get_session), _: Principal = Depends(require("analyst"))):
    return _line_json(session, _svc(service.set_line_status, session, line_id, body.status))


@router.get("/purchase-orders/{po_id}/cross-check")
def po_cross_check(po_id: int, session: Session = Depends(get_session), _: Principal = Depends(require("analyst"))):
    return service.cross_check(session, po_id)
