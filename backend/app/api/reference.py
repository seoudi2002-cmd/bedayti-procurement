"""Reference library API: files kept as versioned reference sources (asset register, regulations, annual report ...)."""
from datetime import date
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import Principal, require
from app.core.reference import service
from app.db import get_engine, get_session
from app.models import AssetRegisterRow, ExtractedPage, ReferenceSource

router = APIRouter(prefix="/reference")


def _background(source_id: int) -> None:
    with Session(get_engine()) as s:
        service.process_document_job(s, source_id)


def _get(session: Session, rid: int) -> ReferenceSource:
    src = session.get(ReferenceSource, rid)
    if src is None:
        raise HTTPException(404, "Reference not found")
    return src


@router.post("", status_code=201)
async def upload(background: BackgroundTasks, file: UploadFile = File(...), kind: str | None = Form(None), series: str | None = Form(None), title: str | None = Form(None),
                 as_of: str | None = Form(None), notes: str | None = Form(None), session: Session = Depends(get_session), principal: Principal = Depends(require("analyst"))):
    try:
        when = date.fromisoformat(as_of) if as_of else None
    except ValueError as exc:
        raise HTTPException(422, "as_of must be YYYY-MM-DD") from exc
    content = await file.read()
    try:
        src = service.register(session, content, file.filename or "file", principal.name, kind, series, title, when, notes)
    except service.ReferenceError as exc:
        raise HTTPException(exc.status, exc.detail) from exc
    if src.status == "processing":
        background.add_task(_background, src.id)
    return service.meta(src, detail=True)


@router.get("")
def list_sources(kind: str | None = None, series: str | None = None, current_only: bool = False, session: Session = Depends(get_session),
                 principal: Principal = Depends(require("viewer"))):
    q = select(ReferenceSource).order_by(ReferenceSource.series_key, ReferenceSource.version_no.desc())
    if kind:
        q = q.where(ReferenceSource.kind == kind)
    if series:
        q = q.where(ReferenceSource.series_key == series)
    if current_only:
        q = q.where(ReferenceSource.is_current.is_(True))
    return [service.meta(s) for s in session.scalars(q)]


@router.get("/{rid}")
def detail(rid: int, session: Session = Depends(get_session), principal: Principal = Depends(require("viewer"))):
    src = _get(session, rid)
    if src.status == "processing":
        service.finalize_document(session, rid)
    return service.meta(src, detail=True)


@router.patch("/{rid}")
def update(rid: int, values: dict, session: Session = Depends(get_session), principal: Principal = Depends(require("admin"))):
    src = _get(session, rid)
    allowed = {"title", "notes", "as_of"}
    if set(values) - allowed:
        raise HTTPException(422, f"Only {sorted(allowed)} can be edited (the stored content is never changed)")
    if "title" in values:
        src.title = values["title"]
    if "notes" in values:
        src.notes = values["notes"]
    if "as_of" in values:
        try:
            src.as_of_date = date.fromisoformat(values["as_of"]) if values["as_of"] else None
        except ValueError as exc:
            raise HTTPException(422, "as_of must be YYYY-MM-DD") from exc
        src.as_of_source = "uploader" if values["as_of"] else "none"
    session.commit()
    service._refresh_current(session, src.series_key)
    return service.meta(src, detail=True)


@router.get("/{rid}/assets")
def asset_rows(rid: int, q: str | None = None, location: str | None = None, category: str | None = None, limit: int = Query(100, le=1000), offset: int = 0,
               session: Session = Depends(get_session), principal: Principal = Depends(require("viewer"))):
    src = _get(session, rid)
    if src.kind != "asset_register":
        raise HTTPException(409, "This reference is not an asset register")
    query = select(AssetRegisterRow).where(AssetRegisterRow.source_id == rid).order_by(AssetRegisterRow.row_no)
    if q:
        query = query.where(AssetRegisterRow.description.ilike(f"%{q}%") | (AssetRegisterRow.asset_number == q))
    if location:
        query = query.where(AssetRegisterRow.location_text.ilike(f"%{location}%"))
    if category:
        query = query.where(AssetRegisterRow.major_category == category)
    rows = session.scalars(query.limit(limit).offset(offset)).all()
    cols = ("row_no", "asset_number", "description", "location_text", "major_category", "category_segment", "in_service_date", "in_service_raw", "life_raw", "current_units",
            "cost", "accumulated_depreciation", "net_book_value", "flags")
    return {"version": src.version_no, "as_of": src.as_of_date.isoformat() if src.as_of_date else None, "rows": [{c: getattr(r, c) for c in cols} for r in rows]}


@router.get("/{rid}/pages/{page_no}")
def page_text(rid: int, page_no: int, session: Session = Depends(get_session), principal: Principal = Depends(require("viewer"))):
    src = _get(session, rid)
    if src.job_id is None:
        raise HTTPException(409, "This reference has no page text")
    pg = session.scalar(select(ExtractedPage).where(ExtractedPage.job_id == src.job_id, ExtractedPage.page_no == page_no))
    if pg is None:
        raise HTTPException(404, "Page not found")
    return {"page": pg.page_no, "text_source": pg.text_source, "confidence": None if pg.mean_confidence is None else float(pg.mean_confidence), "text": pg.raw_text}


@router.get("/{rid}/file")
def original(rid: int, session: Session = Depends(get_session), principal: Principal = Depends(require("admin"))):
    src = _get(session, rid)
    if not src.storage_path or not Path(src.storage_path).exists():
        raise HTTPException(404, "Stored file not found")
    return FileResponse(src.storage_path, filename=src.file_name)
