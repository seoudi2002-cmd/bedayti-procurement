"""Vehicle fleet analytics as an analysis-module adapter. Items: "all" and "m:YYYY-MM" (a snapshot up to that month); filter: vehicle."""
import re

from app.core.analysis import AnalysisError, ModuleInfo
from app.core.settings_store import effective_thresholds
from app.modules.vehicle_analysis import engine, report, service


def _focus(item_id) -> str | None:
    s = str(item_id)
    if s == "all":
        return None
    m = re.fullmatch(r"m:(\d{4}-\d{2})", s)
    if not m:
        raise AnalysisError(404, "Item not found")
    return m.group(1)


class VehicleAdapter:
    info = ModuleInfo(
        key="vehicles", module_id="vehicle_analysis", label={"ar": "السيارات", "en": "Vehicles"}, accepts=(".xlsx", ".xlsm", ".xls"), filters={"vehicles": "vehicle"},
        upload_hint={"ar": "بيان الإصلاحات الشهري (Excel) وتقرير استخدام السيارة وكارت الصيانة (xls). كل ملف يُحفظ كنسخة جديدة ولا يستبدل القديمة؛ ويظهر الفرق عند تحديث شهر.",
                     "en": "The monthly repairs statement (Excel), the vehicle usage report and the maintenance card (xls). Each file is kept as a new version and never replaces the older ones; a corrected month shows as a difference."},
        thresholds_key="vehicles.thresholds")

    def ingest(self, session, content, filename, user, options):
        return service.ingest(session, content, filename, user, options)

    def list_items(self, session) -> list[dict]:
        if not service.has_data(session):
            return []
        d = service.load(session)
        periods = sorted({p for v in d["vehicles"] for slot in ("cost", "usage", "service") for p in v[slot]}, reverse=True)
        return [{"id": "all", "label": "Σ " + "السيارات / Vehicles", "layout_label": "all"}] + [
            {"id": f"m:{p}", "label": p, "layout_label": "month", "period": [int(p[:4]), int(p[5:])]} for p in periods]

    def item_meta(self, session, item_id, admin) -> dict:
        _focus(item_id)
        if not service.has_data(session):
            raise AnalysisError(404, "Item not found")
        return {"id": str(item_id), "module": "vehicles", "status": "ready", "versions": service.load(session)["versions"]}

    def delete_item(self, session, item_id) -> None:
        raise AnalysisError(409, "Uploaded files are kept as versions and are never deleted: upload the corrected file instead (it becomes the newest version and the older one stays on record)")

    def build(self, session, item_id, lang, admin, filters):
        focus = _focus(item_id)
        if not service.has_data(session):
            raise AnalysisError(409, "No vehicle files yet: upload the repairs statement")
        th, origin = effective_thresholds(session, "vehicles")
        data = service.load(session)
        filters = {k: v for k, v in (filters or {}).items() if v}
        c = report.C(lang)
        dims = [{"key": "vehicles", "param": "vehicle", "label": c.t("f_vehicle"), "searchable": True, "items": [{"id": v["key"], "label": v["plate"] + (f" · {v['type']}" if v["type"] else "")} for v in data["vehicles"]]}]
        a = engine.analyze(data, th, focus, filters)
        if a.get("empty"):
            raise AnalysisError(409, "The selected filters match nothing")
        if not admin:                       # driver names / notes are personal data
            for s in data["summaries"]:
                pass
        a["versions"] = data["versions"]
        return report.build_report(a, data, th, origin, lang, filters, dims, admin, focus), a

    def api_analysis(self, a: dict) -> dict:
        t = dict(a["totals"])
        t.pop("cur", None)
        return {"totals": t, "months": a["months"], "categories": a["categories"], "vehicles": [{k: v for k, v in r.items() if k != "by_month"} for r in a["vehicles"]], "due": a["due"], "candidates": a["candidates"],
                "thresholds": a["thresholds"], "versions": a.get("versions")}
