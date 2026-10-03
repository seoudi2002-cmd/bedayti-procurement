"""Rent analytics as an analysis-module adapter. Items: "all" (everything recorded) and "m:YYYY-MM" (a snapshot up to that month)."""
import re

from app.core.analysis import AnalysisError, ModuleInfo
from app.core.settings_store import effective_thresholds
from app.modules.rent_analysis import engine, report, service


def _focus(item_id) -> str | None:
    s = str(item_id)
    if s == "all":
        return None
    m = re.fullmatch(r"m:(\d{4}-\d{2})", s)
    if not m:
        raise AnalysisError(404, "Item not found")
    return m.group(1)


class RentAdapter:
    info = ModuleInfo(
        key="rent", module_id="rent_analysis", label={"ar": "الإيجارات", "en": "Rent contracts"}, accepts=(".xlsx", ".xlsm"),
        filters={"governorates": "governorate", "contracts": "contract"},
        upload_hint={"ar": "ملف عقود الإيجار (Excel): ورقة لكل محافظة والمركز الرئيسي. كل ملف يُحفظ كنسخة جديدة ولا يستبدل القديمة؛ والأحدث رفعًا يحدد القيمة السارية.",
                     "en": "The rent contract workbook (Excel): one sheet per governorate plus Head Office. Each file is kept as a new version and never replaces the older ones; the newest upload decides the current value."},
        thresholds_key="rent.thresholds")

    def ingest(self, session, content, filename, user, options):
        return service.ingest(session, content, filename, user, options)

    def list_items(self, session) -> list[dict]:
        if not service.has_data(session):
            return []
        d = service.load(session)
        periods = sorted({p for c in d["contracts"] for p in c["months"]}, reverse=True)
        out = [{"id": "all", "label": "Σ " + "الإيجارات / Rent", "layout_label": "all"}]
        out += [{"id": f"m:{p}", "label": p, "layout_label": "month", "period": [int(p[:4]), int(p[5:])]} for p in periods]
        return out

    def item_meta(self, session, item_id, admin) -> dict:
        _focus(item_id)
        if not service.has_data(session):
            raise AnalysisError(404, "Item not found")
        d = service.load(session)
        return {"id": str(item_id), "module": "rent", "status": "ready", "versions": d["versions"]}

    def delete_item(self, session, item_id) -> None:
        raise AnalysisError(409, "Uploaded files are kept as versions and are never deleted: upload the corrected file instead (it becomes the newest version and the older one stays on record)")

    def build(self, session, item_id, lang, admin, filters):
        focus = _focus(item_id)
        if not service.has_data(session):
            raise AnalysisError(409, "No rent register yet: upload the contract workbook")
        th, origin = effective_thresholds(session, "rent")
        data = service.load(session)
        filters = {k: v for k, v in (filters or {}).items() if v}
        c = report.C(lang)
        govs = sorted({x["governorate"] for x in data["contracts"] if x["governorate"]})
        dims = [{"key": "governorates", "param": "governorate", "label": c.t("f_gov"), "searchable": False,
                 "items": [{"id": g, "label": c.t("hq") if g == "المركز الرئيسي" else g} for g in govs] + ([{"id": "", "label": c.t("unalloc")}] if any(x["governorate"] is None for x in data["contracts"]) else [])},
                {"key": "contracts", "param": "contract", "label": c.t("f_contract"), "searchable": True,
                 "items": [{"id": x["key"], "label": x["name"]} for x in sorted(data["contracts"], key=lambda r: r["name"])]}]
        contracts = engine.apply_filters(data["contracts"], filters) if filters else data["contracts"]
        if filters and not contracts:
            raise AnalysisError(409, "The selected filters match no contracts")
        a = engine.analyze(contracts, th, focus, bool(filters))
        if a.get("empty"):
            raise AnalysisError(409, "No recorded rent values in this scope")
        a["versions"], a["changes_n"] = data["versions"], len(data["changes"])
        return report.build_report(a, data, th, origin, lang, filters, dims, admin, focus), a

    def api_analysis(self, a: dict) -> dict:
        return {"totals": a["totals"], "months": a["months"], "governorates": [{k: v for k, v in g.items() if k != "by_month"} for g in a["governorates"]],
                "quality": a["quality"], "thresholds": a["thresholds"], "versions": a.get("versions"), "changes": a.get("changes_n")}
