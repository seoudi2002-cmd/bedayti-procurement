"""Overtime analytics as an analysis-module adapter. Items: "all" and "m:YYYY-MM" (a snapshot up to that month, annual cumulative included)."""
import re

from app.core.analysis import AnalysisError, ModuleInfo
from app.core.settings_store import effective_thresholds
from app.modules.overtime_analysis import engine, report, service


def _focus(item_id) -> str | None:
    s = str(item_id)
    if s == "all":
        return None
    m = re.fullmatch(r"m:(\d{4}-\d{2})", s)
    if not m:
        raise AnalysisError(404, "Item not found")
    return m.group(1)


class OvertimeAdapter:
    info = ModuleInfo(
        key="overtime", module_id="overtime_analysis", label={"ar": "الأجر الإضافي", "en": "Overtime"}, accepts=(".xlsx", ".xlsm"), filters={"employees": "employee"},
        upload_hint={"ar": "بيان الأجر الإضافي والمأموريات (Excel): ورقة لكل شهر. كل ملف يُحفظ كنسخة جديدة ولا يستبدل القديمة؛ تعديل شهر سابق يظهر كفرق.",
                     "en": "The monthly overtime and missions statement (Excel): one sheet per month. Each file is kept as a new version and never replaces the older ones; a corrected earlier month shows as a difference."},
        thresholds_key="overtime.thresholds")

    def ingest(self, session, content, filename, user, options):
        return service.ingest(session, content, filename, user, options)

    def list_items(self, session) -> list[dict]:
        if not service.has_data(session):
            return []
        d = service.load(session)
        periods = sorted({r["period"] for r in d["roster"]}, reverse=True)
        return [{"id": "all", "label": "Σ " + "الأجر الإضافي / Overtime", "layout_label": "all"}] + [
            {"id": f"m:{p}", "label": p, "layout_label": "month", "period": [int(p[:4]), int(p[5:])]} for p in periods]

    def item_meta(self, session, item_id, admin) -> dict:
        _focus(item_id)
        if not service.has_data(session):
            raise AnalysisError(404, "Item not found")
        return {"id": str(item_id), "module": "overtime", "status": "ready", "versions": service.load(session)["versions"]}

    def delete_item(self, session, item_id) -> None:
        raise AnalysisError(409, "Uploaded files are kept as versions and are never deleted: upload the corrected file instead (it becomes the newest version and the older one stays on record)")

    def build(self, session, item_id, lang, admin, filters):
        focus = _focus(item_id)
        if not service.has_data(session):
            raise AnalysisError(409, "No overtime statement yet: upload the monthly workbook")
        th, origin = effective_thresholds(session, "overtime")
        data = service.load(session)
        filters = {k: v for k, v in (filters or {}).items() if v}
        c = report.C(lang)
        names = {}
        for r in data["roster"]:
            names.setdefault(r["code"], r["name"])
        dims = [{"key": "employees", "param": "employee", "label": c.t("f_emp"), "searchable": True,
                 "items": [{"id": k, "label": (f"{k} · {n}" if admin and n else k)} for k, n in sorted(names.items())]}]
        if focus and not any(r["period"] == focus for r in data["roster"]):
            raise AnalysisError(404, "No statement for this month")
        a = engine.analyze(data["rows"], data["roster"], th, focus, filters)
        if a.get("empty"):
            raise AnalysisError(409, "The selected filters match nothing")
        if not a["avail"]:
            raise AnalysisError(409, "No months available")
        a["versions"] = data["versions"]
        return report.build_report(a, data, th, origin, lang, filters, dims, admin, focus), a

    def api_analysis(self, a: dict) -> dict:
        t = dict(a["totals"])
        t.pop("cur", None)
        return {"totals": t, "months": a["months"], "years": a["years"], "employees": [{k: v for k, v in e.items() if k not in ("by_month", "name")} for e in a["employees"]], "thresholds": a["thresholds"],
                "versions": a.get("versions")}
