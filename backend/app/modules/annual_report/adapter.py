"""Annual report as an analysis-module adapter. It has no upload: it is built from the stored rent, vehicle and overtime data. Items: "y:YYYY"."""
import re

from app.core.analysis import AnalysisError, ModuleInfo
from app.core.settings_store import effective_thresholds
from app.modules.annual_report import engine, report


def _year(item_id) -> int:
    m = re.fullmatch(r"y:(\d{4})", str(item_id))
    if not m:
        raise AnalysisError(404, "Item not found")
    return int(m.group(1))


class AnnualAdapter:
    info = ModuleInfo(
        key="annual", module_id="annual_report", label={"ar": "التقرير السنوي", "en": "Annual report"}, accepts=(), filters={},
        upload_hint={"ar": "لا يُرفع ملف هنا: التقرير يُبنى من بيانات الإيجارات والسيارات والأجر الإضافي المحفوظة، بنفس الأرقام التي تعرضها لوحاتها.",
                     "en": "Nothing is uploaded here: the report is built from the stored rent, vehicle and overtime data, with the same figures their dashboards show."},
        thresholds_key="annual.thresholds")

    def ingest(self, session, content, filename, user, options):
        raise AnalysisError(422, "The annual report is built from the rent, vehicle and overtime data; upload those files in their own tabs")

    def list_items(self, session) -> list[dict]:
        return [{"id": f"y:{y}", "label": str(y), "layout_label": "year", "period": [y, 1]} for y in engine.years(session)]

    def item_meta(self, session, item_id, admin) -> dict:
        y = _year(item_id)
        if y not in engine.years(session):
            raise AnalysisError(404, "No data for this year")
        return {"id": str(item_id), "module": "annual", "status": "ready", "year": y}

    def delete_item(self, session, item_id) -> None:
        raise AnalysisError(409, "The annual report is computed from the stored data and has nothing of its own to delete")

    def build(self, session, item_id, lang, admin, filters):
        y = _year(item_id)
        if y not in engine.years(session):
            raise AnalysisError(404, "No data for this year")
        A = engine.build(session, y)
        data_by = {"rent": A["loads"].get("rent"), "vehicles": A["loads"].get("vehicles"), "overtime": A["loads"].get("overtime")}
        data_by = {k: v for k, v in data_by.items() if v}
        return report.build_report(A, data_by, lang, admin), A

    def api_analysis(self, A: dict) -> dict:
        cb, m = A["combined"], A["modules"]
        return {"year": A["year"], "combined": {k: v for k, v in cb.items() if k not in ("rows", "peak", "low")}, "months": cb["rows"],
                "rent": {"total": m["rent"]["total"], "months": [x["period"] for x in m["rent"]["complete"]]} if m["rent"] else None,
                "fleet": {"total": m["fleet"]["total"], "maint": m["fleet"]["maint"], "fuel": m["fleet"]["fuel"], "months": [x["period"] for x in m["fleet"]["months"]]} if m["fleet"] else None,
                "overtime": {"hours": m["overtime"]["hours"], "weighted": m["overtime"]["weighted"], "months": [x["period"] for x in m["overtime"]["months"]]} if m["overtime"] else None,
                "thresholds": A["thresholds"]}
