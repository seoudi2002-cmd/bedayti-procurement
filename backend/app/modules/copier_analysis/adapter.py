"""Copier analytics as an analysis-module adapter. An *item* is a cycle (one month); the item id "all" is the multi-month trend."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.analysis import AnalysisError, ModuleInfo
from app.core.settings_store import effective_thresholds
from app.models import AnalysisCycle
from app.modules.copier_analysis import engine, report, service


def _filter_machines(machines: list[dict], filters: dict) -> list[dict]:
    g, b, k = set(filters.get("governorates") or ()), set(filters.get("branches") or ()), set(filters.get("classes") or ())
    return [m for m in machines if (not g or m.get("location_group") in g) and (not b or m["branch_key"] in b) and (not k or m["class_key"] in k)]


class CopierAdapter:
    info = ModuleInfo(
        key="copiers", module_id="copier_analysis", label={"ar": "ماكينات التصوير والطباعة", "en": "Copiers & printing machines"},
        accepts=(".xlsx", ".xlsm", ".doc", ".docx", ".pdf"), filters={"governorates": "governorate", "branches": "branch", "classes": "class"},
        upload_hint={"ar": "كشف الاستهلاك الشهري (Excel) وفاتورة المورد (PDF) أساسيان؛ ملف Word وصور صفحات الحالة مساندة فقط",
                     "en": "Monthly consumption statement (Excel) and supplier invoice (PDF) are authoritative; the Word file and scanned status pages are supporting only"},
        thresholds_key="copier.thresholds")

    def _cycle(self, session: Session, item_id) -> AnalysisCycle:
        c = session.get(AnalysisCycle, int(item_id)) if str(item_id).isdigit() else None
        if c is None or c.module_id != "copier_analysis":
            raise AnalysisError(404, "Period not found")
        return c

    def ingest(self, session, content, filename, user, options):
        return service.ingest(session, content, filename, user, options)

    def list_items(self, session) -> list[dict]:
        cycles = session.scalars(select(AnalysisCycle).where(AnalysisCycle.module_id == "copier_analysis").order_by(
            AnalysisCycle.period_year.desc(), AnalysisCycle.period_month.desc())).all()
        out = []
        with_stmt = [c for c in cycles if service.cycle_meta(session, c)["has_statement"]]
        if len(with_stmt) >= 2:
            out.append({"id": "all", "label": "Σ " + " → ".join(c.label for c in reversed(with_stmt)), "trend": True, "layout_label": "trend"})
        for c in cycles:
            m = service.cycle_meta(session, c)
            roles = "+".join(s["role"] for s in m["sources"])
            out.append({"id": c.id, "label": f"{c.label} · {roles}", "period": m["period"], "machines": m["machines"], "status": m["status"],
                        "has_invoice": m["has_invoice"], "layout_label": "cycle"})
        return out

    def item_meta(self, session, item_id, admin) -> dict:
        return service.cycle_meta(session, self._cycle(session, item_id))

    def delete_item(self, session, item_id) -> None:
        service.delete_cycle(session, self._cycle(session, item_id).id)

    # ------------------------------------------------------------------------------------------ build
    def build(self, session, item_id, lang, admin, filters):
        th, origin = effective_thresholds(session, "copier")
        if str(item_id) == "all":
            return self._trend(session, lang, th)
        cycle = self._cycle(session, item_id)
        meta = service.cycle_meta(session, cycle)
        machines = service.load_machines(session, cycle.id)
        if not machines:
            raise AnalysisError(409, "This period has no consumption statement yet; upload the monthly Excel statement first")
        invoice = service.load_invoice(session, cycle.id)
        filters = {k: v for k, v in (filters or {}).items() if v}
        sel = _filter_machines(machines, filters) if filters else machines
        a = engine.analyze_cycle(sel, invoice, th, filtered=bool(filters))
        a["thresholds"], a["thresholds_origin"] = th, origin
        dims = [
            {"key": "governorates", "param": "governorate", "label": report.T[lang]["f_governorates"], "searchable": True,
             "items": [{"id": g, "label": g} for g in sorted({m["location_group"] for m in machines if m.get("location_group")})]},
            {"key": "branches", "param": "branch", "label": report.T[lang]["f_branches"], "searchable": True,
             "items": sorted(({"id": k, "label": v} for k, v in {m["branch_key"]: m["branch_display"] for m in machines}.items()), key=lambda i: i["label"])},
            {"key": "classes", "param": "class", "label": report.T[lang]["f_classes"], "searchable": False,
             "items": [{"id": k, "label": report.C(lang).cls(k)} for k in sorted({m["class_key"] for m in machines})]}]
        evidence = service.load_evidence(session, cycle.id)
        issues = service.cycle_sources_issues(session, cycle.id)
        rm = report.build_cycle_report(meta, a, invoice, evidence, issues, th, origin, lang, filters, dims)
        return rm, a

    def _trend(self, session, lang, th):
        cycles = session.scalars(select(AnalysisCycle).where(AnalysisCycle.module_id == "copier_analysis")).all()
        data = []
        for c in cycles:
            machines = service.load_machines(session, c.id)
            if not machines:
                continue
            invoice = service.load_invoice(session, c.id)
            a = engine.analyze_cycle(machines, invoice, th)
            data.append({"period": (c.period_year, c.period_month), "totals": a["totals"], "machines": machines,
                         "invoice_total": (invoice or {}).get("totals", {}).get("grand_total"), "recon": (a.get("reconciliation") or {}).get("summary")})
        if len(data) < 2:
            raise AnalysisError(409, "A monthly trend needs statements for at least two months")
        trend = engine.analyze_trend(data, th)
        return report.build_trend_report([], trend, lang), {"trend": trend, "thresholds": th, "thresholds_origin": {}}

    def api_analysis(self, a: dict) -> dict:
        if "trend" in a:
            return {"trend": a["trend"]}
        rec = a.get("reconciliation")
        return {"totals": a["totals"], "by_class": a["by_class"], "by_location": a["by_location"], "bands": a["bands"],
                "reconciliation": rec, "unsupported": a["unsupported"], "thresholds": a["thresholds"], "thresholds_origin": a["thresholds_origin"]}
