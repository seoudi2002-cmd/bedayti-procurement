"""Analysis & reporting API (custody analytics first). Upload a management Excel file, get the validated analysis
as JSON, PDF or Excel. Analysis only: no transaction workflow. Holder names are personal data: admin only."""
from dataclasses import asdict
from decimal import Decimal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.auth import Principal, require
from app.core.reporting.excel import ExcelExporter
from app.core.reporting.pdf import PdfExporter
from app.core.settings_store import (
    custody_default_thresholds, effective_thresholds, get_setting, set_setting, validate_thresholds,
)
from app.db import get_session
from app.models import AnalysisDataset
from app.modules.custody_analysis import layouts, service

router = APIRouter(prefix="/analysis/custody")
settings_router = APIRouter(prefix="/settings")


def _dataset(session: Session, dataset_id: int) -> AnalysisDataset:
    ds = session.get(AnalysisDataset, dataset_id)
    if ds is None:
        raise HTTPException(404, "Dataset not found")
    return ds


def _jsonable(o):
    if isinstance(o, Decimal):
        return float(o)
    if isinstance(o, dict):
        return {str(k): _jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    return o


def _meta(ds: AnalysisDataset, admin: bool) -> dict:
    s = ds.summary or {}
    return {"id": ds.id, "layout": ds.layout, "scope": ds.scope_label, "file_name": ds.file_name, "title": ds.title,
            "year": ds.period_year, "year_source": ds.year_source, "facts": ds.facts_count, "months": s.get("months", []),
            "sheets": s.get("sheets", []), "skipped_sheets": s.get("skipped_sheets", []), "issues": s.get("issues", []),
            "controls": s.get("controls", []), "suggested_groups": s.get("suggested_groups", []),
            "created_by": ds.created_by, "created_at": ds.created_at}


@router.post("/datasets", status_code=201)
async def upload(file: UploadFile = File(...), year: int | None = Form(None), layout: str | None = Form(None),
                 scope: str | None = Form(None), session: Session = Depends(get_session),
                 principal: Principal = Depends(require("analyst"))):
    content = await file.read()
    if len(content) > get_settings().max_upload_mb * 1024 * 1024:
        raise HTTPException(413, "File too large")
    if not (file.filename or "").lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(400, "Only Excel workbooks (.xlsx) are supported for custody analytics")
    try:
        ds = service.ingest(session, content, file.filename or "upload.xlsx", principal.name, year, layout, scope)
    except service.DuplicateDataset as exc:
        raise HTTPException(409, {"message": str(exc), "dataset_id": exc.dataset_id}) from exc
    except layouts.UnrecognisedLayout as exc:
        raise HTTPException(422, str(exc)) from exc
    except Exception as exc:  # an unreadable workbook must not become a 500
        if exc.__class__.__name__ in ("BadZipFile", "InvalidFileException"):
            raise HTTPException(400, "The file is not a readable Excel workbook") from exc
        raise
    return _meta(ds, principal.at_least("admin"))


@router.get("/datasets")
def list_datasets(session: Session = Depends(get_session), principal: Principal = Depends(require("viewer"))):
    rows = session.scalars(select(AnalysisDataset).order_by(AnalysisDataset.id.desc())).all()
    return [{"id": d.id, "layout": d.layout, "scope": d.scope_label, "file_name": d.file_name, "facts": d.facts_count,
             "months": (d.summary or {}).get("months", []), "year": d.period_year, "created_at": d.created_at} for d in rows]


@router.get("/datasets/{dataset_id}")
def dataset(dataset_id: int, session: Session = Depends(get_session), principal: Principal = Depends(require("viewer"))):
    return _meta(_dataset(session, dataset_id), principal.at_least("admin"))


@router.delete("/datasets/{dataset_id}", status_code=204)
def delete(dataset_id: int, session: Session = Depends(get_session), principal: Principal = Depends(require("admin"))):
    _dataset(session, dataset_id)
    service.delete_dataset(session, dataset_id)


def _report(session, dataset_id: int, lang: str, principal: Principal):
    if lang not in ("ar", "en"):
        raise HTTPException(422, "lang must be 'ar' or 'en'")
    ds = _dataset(session, dataset_id)
    return service.build(session, ds, lang, principal.at_least("admin"))


@router.get("/datasets/{dataset_id}/report")
def report_json(dataset_id: int, lang: str = "ar", session: Session = Depends(get_session),
                principal: Principal = Depends(require("viewer"))):
    rm, a = _report(session, dataset_id, lang, principal)
    return _jsonable({"report": asdict(rm), "analysis": {k: a[k] for k in (
        "total", "capabilities", "periods", "by_category", "by_scope", "by_branch", "by_group", "outliers", "variance",
        "unsupported", "thresholds", "thresholds_origin")}})


@router.get("/datasets/{dataset_id}/report.pdf")
def report_pdf(dataset_id: int, lang: str = "ar", session: Session = Depends(get_session),
               principal: Principal = Depends(require("viewer"))):
    rm, _ = _report(session, dataset_id, lang, principal)
    return Response(PdfExporter().render(rm), media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="custody_analysis_{dataset_id}_{lang}.pdf"'})


@router.get("/datasets/{dataset_id}/report.xlsx")
def report_xlsx(dataset_id: int, lang: str = "ar", session: Session = Depends(get_session),
                principal: Principal = Depends(require("viewer"))):
    rm, _ = _report(session, dataset_id, lang, principal)
    return Response(ExcelExporter().render(rm),
                    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f'attachment; filename="custody_analysis_{dataset_id}_{lang}.xlsx"'})


# ------------------------------------------------------------------ settings (admin; no code change needed)
@settings_router.get("/custody.thresholds")
def get_thresholds(session: Session = Depends(get_session), principal: Principal = Depends(require("viewer"))):
    eff, origin = effective_thresholds(session)
    return {"effective": eff, "origin": origin, "defaults": custody_default_thresholds()}


@settings_router.put("/custody.thresholds")
def put_thresholds(values: dict, session: Session = Depends(get_session), principal: Principal = Depends(require("admin"))):
    try:
        merged = {**(get_setting(session, "custody.thresholds", {}) or {}), **validate_thresholds(values)}
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    set_setting(session, "custody.thresholds", merged, principal.name)
    eff, origin = effective_thresholds(session)
    return {"effective": eff, "origin": origin}


@settings_router.get("/custody.display_taxonomy")
def get_taxonomy(session: Session = Depends(get_session), principal: Principal = Depends(require("viewer"))):
    return get_setting(session, "custody.display_taxonomy", {"groups": {}})


@settings_router.put("/custody.display_taxonomy")
def put_taxonomy(value: dict, session: Session = Depends(get_session), principal: Principal = Depends(require("admin"))):
    groups = value.get("groups")
    if not isinstance(groups, dict) or any(not isinstance(v, list) or not all(isinstance(m, str) for m in v) for v in groups.values()):
        raise HTTPException(422, 'Expected {"groups": {"<display group>": ["<source category>", ...]}}')
    seen: dict[str, str] = {}
    for g, members in groups.items():
        for m in members:
            if m in seen:
                raise HTTPException(422, f"Category '{m}' is in two groups ('{seen[m]}' and '{g}')")
            seen[m] = g
    set_setting(session, "custody.display_taxonomy", {"groups": groups}, principal.name)  # original names are never altered
    return {"groups": groups}


@settings_router.get("/custody.branch_key")
def get_branch_key(session: Session = Depends(get_session), principal: Principal = Depends(require("viewer"))):
    return get_setting(session, "custody.branch_key", {"mode": "cost_center"})


@settings_router.put("/custody.branch_key")
def put_branch_key(value: dict, session: Session = Depends(get_session), principal: Principal = Depends(require("admin"))):
    if value.get("mode") not in ("cost_center", "name"):
        raise HTTPException(422, "mode must be 'cost_center' or 'name'")
    set_setting(session, "custody.branch_key", {"mode": value["mode"]}, principal.name)
    return {"mode": value["mode"]}
