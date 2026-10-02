from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.auth import Principal, require
from app.core.exceptions import decide_exception
from app.core.ingestion.pipeline import DuplicateUploadError, stage_file, validate_batch
from app.core.ingestion.readers import UnsupportedFileError
from app.core.intake import analyze_file
from app.core import overrides as ov
from app.core.kpi.engine import compute_kpi
from app.core.mapping.engine import header_signature, suggest_mapping
from app.core.modules.loader import LoaderNotImplemented, get_loader
from app.core.modules.registry import get_registry
from app.db import get_session
from app.models import DataException
from app.models.meta import ImportBatch, ValidationIssue

router = APIRouter()


def _module(module_id: str):
    try:
        return get_registry().get(module_id)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc


def _guard_module(principal: Principal, module_id: str) -> None:
    """Modules holding personal data (HR, contacts) are admin-only end to end."""
    if _module(module_id).manifest.contains_personal_data and not principal.at_least("admin"):
        raise HTTPException(403, "This module contains personal data: admin role required")


def _batch(session: Session, batch_id: int, principal: Principal) -> ImportBatch:
    batch = session.get(ImportBatch, batch_id)
    if batch is None:
        raise HTTPException(404, "Batch not found")
    _guard_module(principal, batch.module_id)
    return batch


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/modules")
def list_modules(_: Principal = Depends(require("viewer"))):
    return [
        {**m.manifest.model_dump(), "kpis": [k.code for k in m.kpis], "field_count": len(m.schema_.fields)}
        for m in get_registry().all()
    ]


@router.get("/modules/{module_id}")
def module_detail(module_id: str, _: Principal = Depends(require("viewer"))):
    m = _module(module_id)
    return {"manifest": m.manifest, "schema": m.schema_, "profile_schemas": m.profile_schemas,
            "kpis": m.kpis, "rules": m.rules}


@router.post("/intake/analyze")
async def intake_analyze(file: UploadFile = File(...), _: Principal = Depends(require("analyst"))):
    """Which module/profile does each sheet of this file look like? (nothing is stored)"""
    content = await file.read()
    try:
        return {"file": file.filename, "sheets": analyze_file(get_registry(), file.filename or "upload", content)}
    except UnsupportedFileError as exc:
        raise HTTPException(415, str(exc)) from exc


@router.post("/intake/profile")
async def intake_profile(file: UploadFile = File(...), show_values: bool = False, ocr_pages: int = 0,
                         principal: Principal = Depends(require("analyst"))):
    """Structure profile of an unknown file (sheets, columns, types, fill rates, merged cells ...). Cell values are
    only included when show_values is requested by an admin: a profile is safe to share by default."""
    from app.core.profiling import profile_file
    if show_values and not principal.at_least("admin"):
        raise HTTPException(403, "show_values may expose personal data: admin role required")
    content = await file.read()
    try:
        return {"file": file.filename, "profile": profile_file(file.filename or "upload", content, show_values, min(ocr_pages, 6))}
    except ValueError as exc:
        raise HTTPException(415, str(exc)) from exc


@router.post("/imports", status_code=201)
async def upload(
    module_id: str = Form(...), file: UploadFile = File(...), sheet: str | None = Form(None),
    header_row: int | None = Form(None), profile: str = Form("default"),
    session: Session = Depends(get_session), principal: Principal = Depends(require("analyst")),
):
    _guard_module(principal, module_id)
    spec = _module(module_id)
    content = await file.read()
    if len(content) > get_settings().max_upload_mb * 1024 * 1024:
        raise HTTPException(413, "File too large")
    try:
        schema = spec.schema_for(profile)
        batch, table = stage_file(session, spec, file.filename or "upload", content, sheet, header_row,
                                  created_by=principal.name, profile=profile)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    except DuplicateUploadError as exc:
        raise HTTPException(409, str(exc)) from exc
    except UnsupportedFileError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {
        "batch_id": batch.id, "profile": profile, "rows": batch.rows_total, "sheet": table.sheet_name,
        "sheets": table.sheet_names, "header_row": table.header_row, "headers": table.headers,
        "suggested_mapping": suggest_mapping(table.headers, schema),
        "header_signature": header_signature(table.headers),
    }


@router.post("/imports/{batch_id}/validate")
def validate(batch_id: int, column_map: dict[str, str] | None = None, session: Session = Depends(get_session),
             principal: Principal = Depends(require("analyst"))):
    batch = _batch(session, batch_id, principal)
    try:
        batch = validate_batch(session, _module(batch.module_id), batch, column_map)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {"batch_id": batch.id, "status": batch.status, "rows_valid": batch.rows_valid,
            "rows_rejected": batch.rows_rejected, "rows_skipped": batch.rows_skipped}


@router.post("/imports/{batch_id}/load")
def load(batch_id: int, session: Session = Depends(get_session), principal: Principal = Depends(require("analyst"))):
    batch = _batch(session, batch_id, principal)
    if batch.status not in ("validated", "partially_loaded", "loaded"):
        raise HTTPException(409, "Validate the batch before loading (or resolve reviews and reload a partial one)")
    try:
        written = get_loader(batch.module_id).load(session, batch)
    except LoaderNotImplemented as exc:
        raise HTTPException(501, str(exc)) from exc
    return {"batch_id": batch.id, "status": batch.status, "rows_loaded": written, "rows_held": batch.rows_held,
            "warnings": batch.warnings or []}


@router.post("/imports/{batch_id}/rollback")
def rollback_import(batch_id: int, session: Session = Depends(get_session),
                    principal: Principal = Depends(require("analyst"))):
    batch = _batch(session, batch_id, principal)
    loader = get_loader(batch.module_id)
    try:
        loader.rollback(session, batch)
    except (NotImplementedError, AttributeError) as exc:
        raise HTTPException(501, str(exc) or "Rollback is not available for this module") from exc
    return {"batch_id": batch.id, "status": batch.status}


@router.get("/imports/{batch_id}")
def batch_detail(batch_id: int, session: Session = Depends(get_session),
                 principal: Principal = Depends(require("analyst"))):
    batch = _batch(session, batch_id, principal)
    issues = session.scalars(select(ValidationIssue).where(
        ValidationIssue.batch_id == batch_id, ValidationIssue.severity != "info").limit(200)).all()
    return {
        "batch_id": batch.id, "module_id": batch.module_id, "profile": batch.profile, "file_name": batch.file_name,
        "status": batch.status, "rows_total": batch.rows_total, "rows_valid": batch.rows_valid,
        "rows_rejected": batch.rows_rejected, "rows_skipped": batch.rows_skipped, "rows_loaded": batch.rows_loaded,
        "rows_held": batch.rows_held, "warnings": batch.warnings or [],
        "issues": [{"row_id": i.raw_row_id, "severity": i.severity, "code": i.code, "field": i.field,
                    "message": i.message} for i in issues],
    }


@router.get("/kpis/{module_id}/{kpi_code}")
def kpi_value(module_id: str, kpi_code: str, date_from: date | None = None, date_to: date | None = None,
              group_by: str | None = None, session: Session = Depends(get_session),
              _: Principal = Depends(require("viewer"))):
    spec = _module(module_id)
    try:
        result = compute_kpi(session, spec, kpi_code, date_from, date_to, group_by)
    except KeyError as exc:
        raise HTTPException(404, f"Unknown KPI {kpi_code}") from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {"module": module_id, "kpi": kpi_code, "group_by": group_by,
            "values": [{"key": k, "value": v} for k, v in result.items()]}


class ExceptionDecision(BaseModel):
    status: str  # accepted | resolved | dismissed | open
    note: str | None = None


@router.get("/exceptions")
def list_exceptions(status: str = "open", module_id: str | None = None, code: str | None = None,
                    severity: str | None = None, limit: int = 200, session: Session = Depends(get_session),
                    _: Principal = Depends(require("analyst"))):
    q = select(DataException).where(DataException.status == status).order_by(
        DataException.severity, DataException.code, DataException.entity_key).limit(min(limit, 1000))
    if module_id:
        q = q.where(DataException.module_id == module_id)
    if code:
        q = q.where(DataException.code == code)
    if severity:
        q = q.where(DataException.severity == severity)
    return [{"id": e.id, "module_id": e.module_id, "code": e.code, "severity": e.severity, "status": e.status,
             "entity_type": e.entity_type, "entity_key": e.entity_key, "message": e.message, "details": e.details,
             "decided_by": e.decided_by, "decision_note": e.decision_note} for e in session.scalars(q)]


@router.post("/exceptions/{exception_id}/decide")
def decide(exception_id: int, body: ExceptionDecision, session: Session = Depends(get_session),
           principal: Principal = Depends(require("analyst"))):
    try:
        row = decide_exception(session, exception_id, body.status, principal.name, body.note)
    except KeyError as exc:
        raise HTTPException(404, "Exception not found") from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {"id": row.id, "status": row.status, "decided_by": row.decided_by}


# ---------------------------------------------------------------- corrections (override layer)
class CorrectionIn(BaseModel):
    entity_type: str
    entity_key: str
    field: str
    corrected_value: str | None
    reason: str
    auto_approve: bool = False


class RowCorrectionIn(BaseModel):
    batch_id: int
    row_number: int
    field: str
    corrected_value: str
    reason: str


class ReviewIn(BaseModel):
    note: str | None = None


def _ov_json(o) -> dict:
    return {"id": o.id, "entity_type": o.entity_type, "entity_key": o.entity_key, "field": o.field,
            "original_value": o.original_value, "corrected_value": o.corrected_value, "reason": o.reason,
            "proposed_by": o.proposed_by, "proposed_at": o.created_at, "status": o.status,
            "reviewed_by": o.reviewed_by, "reviewed_at": o.reviewed_at, "review_note": o.review_note,
            "applied_at": o.applied_at}


def _ov_call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except ov.OverrideError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post("/corrections", status_code=201)
def propose_correction(body: CorrectionIn, session: Session = Depends(get_session),
                       principal: Principal = Depends(require("analyst"))):
    row = _ov_call(ov.propose, session, body.entity_type, body.entity_key, body.field, body.corrected_value,
                   body.reason, principal.name, body.auto_approve)
    return _ov_json(row)


@router.post("/corrections/source-row", status_code=201)
def propose_row_correction(body: RowCorrectionIn, session: Session = Depends(get_session),
                           principal: Principal = Depends(require("analyst"))):
    batch = _batch(session, body.batch_id, principal)
    row = _ov_call(ov.propose_row_correction, session, batch, body.row_number, body.field, body.corrected_value,
                   body.reason, principal.name)
    return _ov_json(row)


@router.get("/corrections")
def list_corrections(status: str | None = None, entity_type: str | None = None, entity_key: str | None = None,
                     session: Session = Depends(get_session), _: Principal = Depends(require("analyst"))):
    from app.models import DataOverride
    q = select(DataOverride).order_by(DataOverride.id.desc()).limit(500)
    if status:
        q = q.where(DataOverride.status == status)
    if entity_type:
        q = q.where(DataOverride.entity_type == entity_type)
    if entity_key:
        q = q.where(DataOverride.entity_key == entity_key)
    return [_ov_json(o) for o in session.scalars(q)]


@router.post("/corrections/{correction_id}/approve")
def approve_correction(correction_id: int, body: ReviewIn, session: Session = Depends(get_session),
                       principal: Principal = Depends(require("analyst"))):
    return _ov_json(_ov_call(ov.approve, session, correction_id, principal.name, body.note))


@router.post("/corrections/{correction_id}/reject")
def reject_correction(correction_id: int, body: ReviewIn, session: Session = Depends(get_session),
                      principal: Principal = Depends(require("analyst"))):
    return _ov_json(_ov_call(ov.reject, session, correction_id, principal.name, body.note))


@router.post("/corrections/{correction_id}/revert")
def revert_correction(correction_id: int, body: ReviewIn, session: Session = Depends(get_session),
                      principal: Principal = Depends(require("analyst"))):
    return _ov_json(_ov_call(ov.revert, session, correction_id, principal.name, body.note))
