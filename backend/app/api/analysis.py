"""Generic analysis & reporting API: /api/analysis/<module>/... for every analysis module registered in
app.core.analysis.registry (custody, copiers, ...). Upload a management file, get the validated analysis as JSON, PDF or
Excel. Analysis only: no transaction workflow. Personal data is admin-only (decided inside each module's report)."""
from dataclasses import asdict
from decimal import Decimal

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Request, Response, UploadFile
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.analysis import AnalysisError
from app.core.analysis.registry import adapters, get_adapter
from app.core.auth import Principal, require
from app.core.reporting.excel import ExcelExporter
from app.core.reporting.pdf import PdfExporter
from app.core.settings_store import (
    KNOWN_KEYS, default_thresholds, effective_thresholds, get_setting, set_setting, validate_thresholds,
)
from app.db import get_session

router = APIRouter(prefix="/analysis")
settings_router = APIRouter(prefix="/settings")


def _adapter(key: str):
    try:
        return get_adapter(key)
    except AnalysisError as exc:
        raise HTTPException(exc.status, exc.detail) from exc


def _jsonable(o):
    if isinstance(o, Decimal):
        return float(o)
    if isinstance(o, dict):
        return {str(k): _jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple, set)):
        return [_jsonable(v) for v in o]
    return o


@router.get("")
def modules(principal: Principal = Depends(require("viewer"))):
    return [{"key": a.info.key, "label": a.info.label, "accepts": list(a.info.accepts), "upload_hint": a.info.upload_hint,
             "filters": a.info.filters} for a in adapters().values()]


@router.post("/{key}/datasets", status_code=201)
async def upload(key: str, background: BackgroundTasks, response: Response, file: UploadFile = File(...),
                 year: int | None = Form(None), layout: str | None = Form(None), scope: str | None = Form(None),
                 session: Session = Depends(get_session), principal: Principal = Depends(require("analyst"))):
    ad = _adapter(key)
    content = await file.read()
    if len(content) > get_settings().max_upload_mb * 1024 * 1024:
        raise HTTPException(413, "File too large")
    try:
        res = ad.ingest(session, content, file.filename or "upload", principal.name, {"year": year, "layout": layout, "scope": scope})
    except AnalysisError as exc:
        raise HTTPException(exc.status, exc.detail) from exc
    if res.background:
        background.add_task(res.background)
    response.status_code = res.status
    return res.meta


@router.get("/{key}/datasets")
def list_items(key: str, session: Session = Depends(get_session), principal: Principal = Depends(require("viewer"))):
    return _jsonable(_adapter(key).list_items(session))


@router.get("/{key}/datasets/{item_id}")
def item(key: str, item_id: str, session: Session = Depends(get_session), principal: Principal = Depends(require("viewer"))):
    try:
        return _jsonable(_adapter(key).item_meta(session, item_id, principal.at_least("admin")))
    except AnalysisError as exc:
        raise HTTPException(exc.status, exc.detail) from exc


@router.delete("/{key}/datasets/{item_id}", status_code=204)
def delete(key: str, item_id: str, session: Session = Depends(get_session), principal: Principal = Depends(require("admin"))):
    try:
        _adapter(key).delete_item(session, item_id)
    except AnalysisError as exc:
        raise HTTPException(exc.status, exc.detail) from exc


def _report(request: Request, key: str, item_id: str, lang: str, session: Session, principal: Principal):
    if lang not in ("ar", "en"):
        raise HTTPException(422, "lang must be 'ar' or 'en'")
    ad = _adapter(key)
    filters = {fk: request.query_params.getlist(param) for fk, param in ad.info.filters.items()}
    try:
        rm, a = ad.build(session, item_id, lang, principal.at_least("admin"), filters)
    except AnalysisError as exc:
        raise HTTPException(exc.status, exc.detail) from exc
    return ad, rm, a


@router.get("/{key}/datasets/{item_id}/report")
def report_json(request: Request, key: str, item_id: str, lang: str = "ar", session: Session = Depends(get_session),
                principal: Principal = Depends(require("viewer"))):
    ad, rm, a = _report(request, key, item_id, lang, session, principal)
    return _jsonable({"report": asdict(rm), "analysis": ad.api_analysis(a)})


@router.get("/{key}/datasets/{item_id}/report.pdf")
def report_pdf(request: Request, key: str, item_id: str, lang: str = "ar", session: Session = Depends(get_session),
               principal: Principal = Depends(require("viewer"))):
    _, rm, _a = _report(request, key, item_id, lang, session, principal)
    return Response(PdfExporter().render(rm), media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{key}_analysis_{item_id}_{lang}.pdf"'})


@router.get("/{key}/datasets/{item_id}/report.xlsx")
def report_xlsx(request: Request, key: str, item_id: str, lang: str = "ar", session: Session = Depends(get_session),
                principal: Principal = Depends(require("viewer"))):
    _, rm, _a = _report(request, key, item_id, lang, session, principal)
    return Response(ExcelExporter().render(rm),
                    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f'attachment; filename="{key}_analysis_{item_id}_{lang}.xlsx"'})


# ------------------------------------------------------------------ settings (admin; no code change needed)
def _threshold_module(name: str) -> str:
    module = name.split(".")[0]
    if name != f"{module}.thresholds" or name not in KNOWN_KEYS:
        raise HTTPException(404, "Unknown setting")
    return module


@settings_router.get("/{name}.thresholds")
def get_thresholds(name: str, session: Session = Depends(get_session), principal: Principal = Depends(require("viewer"))):
    module = _threshold_module(f"{name}.thresholds")
    eff, origin = effective_thresholds(session, module)
    return {"effective": eff, "origin": origin, "defaults": default_thresholds(module)}


@settings_router.put("/{name}.thresholds")
def put_thresholds(name: str, values: dict, session: Session = Depends(get_session), principal: Principal = Depends(require("admin"))):
    module = _threshold_module(f"{name}.thresholds")
    try:
        merged = {**(get_setting(session, f"{module}.thresholds", {}) or {}), **validate_thresholds(values, module)}
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    set_setting(session, f"{module}.thresholds", merged, principal.name)
    eff, origin = effective_thresholds(session, module)
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
