"""Custody analytics as an analysis-module adapter (the platform's generic API/dashboard call this)."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.analysis import AnalysisError, ModuleInfo, UploadResult
from app.models import AnalysisDataset
from app.modules.custody_analysis import layouts, service


class CustodyAdapter:
    info = ModuleInfo(
        key="custody", module_id="custody_analysis", label={"ar": "العهد المالية", "en": "Financial custody"},
        accepts=(".xlsx", ".xlsm"), filters={"periods": "period", "branches": "branch", "categories": "category"},
        upload_hint={"ar": "ملف Excel: قيود تسوية العهد المؤقتة، أو تحليل مصروفات الفروع، أو المركز الرئيسي",
                     "en": "Excel: temporary-custody settlement journal, branch expenses or Head Office expenses"},
        thresholds_key="custody.thresholds")

    def _ds(self, session: Session, item_id) -> AnalysisDataset:
        ds = session.get(AnalysisDataset, int(item_id)) if str(item_id).isdigit() else None
        if ds is None or ds.module_id != "custody_analysis":
            raise AnalysisError(404, "Dataset not found")
        return ds

    def meta(self, ds: AnalysisDataset) -> dict:
        s = ds.summary or {}
        return {"id": ds.id, "module": "custody", "layout": ds.layout, "scope": ds.scope_label, "file_name": ds.file_name,
                "title": ds.title, "year": ds.period_year, "year_source": ds.year_source, "facts": ds.facts_count,
                "months": s.get("months", []), "sheets": s.get("sheets", []), "skipped_sheets": s.get("skipped_sheets", []),
                "issues": s.get("issues", []), "controls": s.get("controls", []), "suggested_groups": s.get("suggested_groups", []),
                "created_by": ds.created_by, "created_at": ds.created_at, "status": "ready"}

    def ingest(self, session, content, filename, user, options) -> UploadResult:
        if not filename.lower().endswith((".xlsx", ".xlsm")):
            raise AnalysisError(400, "Only Excel workbooks (.xlsx) are supported for custody analytics")
        try:
            ds = service.ingest(session, content, filename, user, options.get("year"), options.get("layout"), options.get("scope"))
        except service.DuplicateDataset as exc:
            raise AnalysisError(409, {"message": str(exc), "dataset_id": exc.dataset_id}) from exc
        except layouts.UnrecognisedLayout as exc:
            raise AnalysisError(422, str(exc)) from exc
        except Exception as exc:  # an unreadable workbook must not become a 500
            if exc.__class__.__name__ in ("BadZipFile", "InvalidFileException"):
                raise AnalysisError(400, "The file is not a readable Excel workbook") from exc
            raise
        return UploadResult(ds.id, self.meta(ds))

    def list_items(self, session) -> list[dict]:
        rows = session.scalars(select(AnalysisDataset).where(AnalysisDataset.module_id == "custody_analysis")
                               .order_by(AnalysisDataset.id.desc())).all()
        return [{"id": d.id, "layout": d.layout, "scope": d.scope_label, "file_name": d.file_name, "facts": d.facts_count,
                 "months": (d.summary or {}).get("months", []), "year": d.period_year, "created_at": d.created_at,
                 "label": f"#{d.id} · {d.file_name}", "layout_label": d.layout} for d in rows]

    def item_meta(self, session, item_id, admin) -> dict:
        return self.meta(self._ds(session, item_id))

    def delete_item(self, session, item_id) -> None:
        self._ds(session, item_id)
        service.delete_dataset(session, int(item_id))

    def build(self, session, item_id, lang, admin, filters):
        ds = self._ds(session, item_id)
        return service.build(session, ds, lang, admin, filters)

    def api_analysis(self, a: dict) -> dict:
        return {k: a[k] for k in ("total", "capabilities", "periods", "by_category", "by_scope", "by_branch", "by_group",
                                  "outliers", "variance", "unsupported", "thresholds", "thresholds_origin")}
