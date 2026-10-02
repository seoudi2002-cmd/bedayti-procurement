from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.ingestion.pipeline import DuplicateUploadError, stage_file, validate_batch
from app.core.ingestion.readers import UnsupportedFileError
from app.core.kpi.engine import compute_kpi
from app.core.mapping.engine import header_signature, suggest_mapping
from app.core.modules.loader import LoaderNotImplemented, get_loader
from app.core.modules.registry import get_registry
from app.db import get_session
from app.models.meta import ImportBatch, ValidationIssue

router = APIRouter()


def _module(module_id: str):
    try:
        return get_registry().get(module_id)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/modules")
def list_modules():
    return [
        {**m.manifest.model_dump(), "kpis": [k.code for k in m.kpis], "field_count": len(m.schema_.fields)}
        for m in get_registry().all()
    ]


@router.get("/modules/{module_id}")
def module_detail(module_id: str):
    m = _module(module_id)
    return {"manifest": m.manifest, "schema": m.schema_, "kpis": m.kpis, "rules": m.rules}


@router.post("/imports", status_code=201)
async def upload(
    module_id: str = Form(...), file: UploadFile = File(...), sheet: str | None = Form(None),
    header_row: int | None = Form(None), session: Session = Depends(get_session),
):
    spec = _module(module_id)
    content = await file.read()
    if len(content) > get_settings().max_upload_mb * 1024 * 1024:
        raise HTTPException(413, "File too large")
    try:
        batch, table = stage_file(session, spec, file.filename or "upload", content, sheet, header_row)
    except DuplicateUploadError as exc:
        raise HTTPException(409, str(exc)) from exc
    except UnsupportedFileError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {
        "batch_id": batch.id, "rows": batch.rows_total, "sheet": table.sheet_name, "sheets": table.sheet_names,
        "header_row": table.header_row, "headers": table.headers,
        "suggested_mapping": suggest_mapping(table.headers, spec.schema_),
        "header_signature": header_signature(table.headers),
    }


@router.post("/imports/{batch_id}/validate")
def validate(batch_id: int, column_map: dict[str, str] | None = None, session: Session = Depends(get_session)):
    batch = session.get(ImportBatch, batch_id)
    if batch is None:
        raise HTTPException(404, "Batch not found")
    try:
        batch = validate_batch(session, _module(batch.module_id), batch, column_map)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {"batch_id": batch.id, "status": batch.status, "rows_valid": batch.rows_valid,
            "rows_rejected": batch.rows_rejected}


@router.post("/imports/{batch_id}/load")
def load(batch_id: int, session: Session = Depends(get_session)):
    batch = session.get(ImportBatch, batch_id)
    if batch is None:
        raise HTTPException(404, "Batch not found")
    if batch.status != "validated":
        raise HTTPException(409, "Validate the batch before loading")
    try:
        written = get_loader(batch.module_id).load(session, batch)
    except LoaderNotImplemented as exc:
        raise HTTPException(501, str(exc)) from exc
    return {"batch_id": batch.id, "rows_loaded": written}


@router.get("/imports/{batch_id}")
def batch_detail(batch_id: int, session: Session = Depends(get_session)):
    batch = session.get(ImportBatch, batch_id)
    if batch is None:
        raise HTTPException(404, "Batch not found")
    issues = session.scalars(select(ValidationIssue).where(ValidationIssue.batch_id == batch_id).limit(200)).all()
    return {
        "batch_id": batch.id, "module_id": batch.module_id, "file_name": batch.file_name, "status": batch.status,
        "rows_total": batch.rows_total, "rows_valid": batch.rows_valid, "rows_rejected": batch.rows_rejected,
        "issues": [{"row_id": i.raw_row_id, "severity": i.severity, "code": i.code, "field": i.field,
                    "message": i.message} for i in issues],
    }


@router.get("/kpis/{module_id}/{kpi_code}")
def kpi_value(module_id: str, kpi_code: str, date_from: date | None = None, date_to: date | None = None,
              group_by: str | None = None, session: Session = Depends(get_session)):
    spec = _module(module_id)
    try:
        result = compute_kpi(session, spec, kpi_code, date_from, date_to, group_by)
    except KeyError as exc:
        raise HTTPException(404, f"Unknown KPI {kpi_code}") from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {"module": module_id, "kpi": kpi_code, "group_by": group_by,
            "values": [{"key": k, "value": v} for k, v in result.items()]}
