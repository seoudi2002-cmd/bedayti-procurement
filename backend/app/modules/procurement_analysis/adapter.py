"""Procurement register analytics as an analysis-module adapter. One item: "all" (everything loaded); filters: month, supplier, department."""
from app.core.analysis import AnalysisError, ModuleInfo
from app.core.settings_store import effective_thresholds
from app.modules.procurement_analysis import engine, report, service


class ProcurementAdapter:
    info = ModuleInfo(
        key="procurement", module_id="procurement_analysis", label={"ar": "المشتريات", "en": "Procurement"}, accepts=(".xlsx", ".xlsm"),
        filters={"months": "month", "suppliers": "supplier", "departments": "department"},
        upload_hint={"ar": "ملف سجل المشتريات (Excel): سجل الموردين، إشعارات الاحتياج، أوامر الشراء، استلامات المالية؛ وملف فروع الشركة لربط الفروع",
                     "en": "The procurement register workbook (Excel): suppliers, requisitions, purchase orders, finance handover; and the branch master to attribute branches"},
        thresholds_key="procurement.thresholds")

    def ingest(self, session, content, filename, user, options):
        return service.ingest(session, content, filename, user, options)

    def list_items(self, session) -> list[dict]:
        if not service.has_data(session):
            return []
        return [{"id": "all", "label": "Σ " + ("المشتريات / Procurement"), "layout_label": "all"}]

    def item_meta(self, session, item_id, admin) -> dict:
        if str(item_id) != "all" or not service.has_data(session):
            raise AnalysisError(404, "Item not found")
        return {"id": "all", "module": "procurement", "status": "ready", "batches": service.load(session)["batches"]}

    def delete_item(self, session, item_id) -> None:
        if str(item_id) != "all" or not service.has_data(session):
            raise AnalysisError(404, "Item not found")
        raise AnalysisError(409, "The registers are cumulative reference data: correct them by uploading the corrected file (loading is an idempotent upsert); they are not deleted from here")

    def build(self, session, item_id, lang, admin, filters):
        if str(item_id) != "all":
            raise AnalysisError(404, "Item not found")
        if not service.has_data(session):
            raise AnalysisError(409, "No procurement registers loaded yet: upload the register workbook")
        th, origin = effective_thresholds(session, "procurement")
        data = service.load(session)
        filters = {k: v for k, v in (filters or {}).items() if v}
        dates = [d for k in ("pos", "requisitions", "memos") for d in (x["date"] for x in data[k]) if d]
        as_of = max(dates) if dates else None
        c = report.C(lang)
        months = sorted({d.strftime("%Y-%m") for d in dates})
        dims = [{"key": "months", "param": "month", "label": c.t("c_month"), "searchable": False, "items": [{"id": m, "label": report.period_label(lang, (int(m[:4]), int(m[5:])))} for m in months]},
                {"key": "suppliers", "param": "supplier", "label": c.t("c_supplier"), "searchable": True,
                 "items": [{"id": s, "label": s} for s in sorted({p["supplier"] for p in data["pos"] if p["supplier"]})]},
                {"key": "departments", "param": "department", "label": c.t("c_dept"), "searchable": False,
                 "items": [{"id": d, "label": d} for d in sorted({r["department"] for r in data["requisitions"] if r["department"]})]}]
        fd = engine.apply_filters(data, filters) if filters else data
        if filters and not (fd["pos"] or fd["requisitions"] or fd["memos"]):
            raise AnalysisError(409, "The selected filters match nothing")
        a = engine.analyze(fd, th, bool(filters), as_of)
        a["thresholds_origin"] = origin
        files = sorted({b["file"] for b in data["batches"]})
        rm = report.build_report(a, data["batches"], data["exceptions"], th, origin, lang, filters, dims, files)
        return rm, a

    def api_analysis(self, a: dict) -> dict:
        return {k: a[k] for k in ("totals", "months", "suppliers", "concentration_pct", "categories", "departments", "pipeline", "attribution", "thresholds")}
