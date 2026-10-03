"""Copier analytics as an analysis-module adapter. An *item* is a cycle (one month); the item id "all" is the multi-month trend."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.analysis import AnalysisError, ModuleInfo
from app.core.settings_store import effective_paper, effective_thresholds
from app.models import AnalysisCycle
from app.modules.copier_analysis import engine, paper, paper_report, report, service


def _filter_machines(machines: list[dict], filters: dict) -> list[dict]:
    g, b, k = set(filters.get("governorates") or ()), set(filters.get("branches") or ()), set(filters.get("classes") or ())
    return [m for m in machines if (not g or m.get("location_group") in g) and (not b or m["branch_key"] in b) and (not k or m["class_key"] in k)]


class CopierAdapter:
    info = ModuleInfo(
        key="copiers", module_id="copier_analysis", label={"ar": "ماكينات التصوير والطباعة", "en": "Copiers & printing machines"},
        accepts=(".xlsx", ".xlsm", ".doc", ".docx", ".pdf"), filters={"governorates": "governorate", "branches": "branch", "classes": "class", "months": "month"},
        upload_hint={"ar": "كشف الاستهلاك الشهري (Excel) وفاتورة المورد (PDF) أساسيان؛ ملف Word وصور صفحات الحالة مساندة فقط؛ وكشف توزيع الورق (Excel) لاستهلاك الورق",
                     "en": "Monthly consumption statement (Excel) and supplier invoice (PDF) are authoritative; the Word file and scanned status pages are supporting only; "
                              "the paper distribution statement (Excel) gives paper consumption"},
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
        pds = service.paper_datasets(session)
        if pds:
            out.append({"id": "paper", "label": "📄 ورق / paper · PO " + ", ".join(str((d.summary or {}).get("po_no") or "—") for d in pds), "layout_label": "paper",
                        "machines": sum(d.facts_count for d in pds), "status": "ready"})
            if len(pds) > 1:
                out += [{"id": f"paper:{d.id}", "label": f"paper · PO {(d.summary or {}).get('po_no') or '—'}", "layout_label": "paper", "status": "ready"} for d in pds]
        for c in cycles:
            m = service.cycle_meta(session, c)
            roles = "+".join(s["role"] for s in m["sources"])
            out.append({"id": c.id, "label": f"{c.label} · {roles}", "period": m["period"], "machines": m["machines"], "status": m["status"],
                        "has_invoice": m["has_invoice"], "layout_label": "cycle"})
        return out

    @staticmethod
    def _paper_id(item_id) -> int | None | bool:
        """False: not a paper item; None: all purchase orders; int: one dataset."""
        sid = str(item_id)
        if sid == "paper":
            return None
        if sid.startswith("paper:") and sid[6:].isdigit():
            return int(sid[6:])
        return False

    def item_meta(self, session, item_id, admin) -> dict:
        pid = self._paper_id(item_id)
        if pid is not False:
            pds = service.paper_datasets(session, pid)
            if not pds:
                raise AnalysisError(404, "Paper distribution not found")
            return {"id": str(item_id), "module": "copiers", "kind": "paper", "sources": [{"dataset_id": d.id, "role": d.role, "file_name": d.file_name, "status": d.status,
                                                                                         "rows": d.facts_count} for d in pds],
                    "issues": [i for d in pds for i in (d.summary or {}).get("issues", [])], "status": "ready"}
        return service.cycle_meta(session, self._cycle(session, item_id))

    def delete_item(self, session, item_id) -> None:
        pid = self._paper_id(item_id)
        if pid is not False:
            if not service.paper_datasets(session, pid):
                raise AnalysisError(404, "Paper distribution not found")
            service.delete_paper(session, pid)
            return
        service.delete_cycle(session, self._cycle(session, item_id).id)

    # ------------------------------------------------------------------------------------------ build
    def build(self, session, item_id, lang, admin, filters):
        th, origin = effective_thresholds(session, "copier")
        pid = self._paper_id(item_id)
        if pid is not False:
            return self._paper(session, pid, lang, filters)
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

    def _paper(self, session, pid, lang, filters):
        stmts = service.load_paper(session, pid)
        if not stmts:
            raise AnalysisError(404, "Paper distribution not found")
        params, origin = effective_paper(session)
        filters = {k: v for k, v in (filters or {}).items() if v}
        units: dict[str, str] = {}
        p = paper_report.P(lang)
        all_rows = [r for s in stmts for r in s["rows"]]
        for r in all_rows:
            units.setdefault(paper.unit_key(r), p.unit({"hq": r["is_head_office"], "name": r["branch_display"], "department": r["department"]}))
        months = sorted({r["distributed_on"].strftime("%Y-%m") for r in all_rows if r["distributed_on"]})
        want_u, want_m = set(filters.get("branches") or ()), set(filters.get("months") or ())
        if want_u or want_m:
            stmts = [{**s, "rows": [r for r in s["rows"] if (not want_u or paper.unit_key(r) in want_u)
                                    and (not want_m or (r["distributed_on"] and r["distributed_on"].strftime("%Y-%m") in want_m))]} for s in stmts]
            stmts = [s for s in stmts if s["rows"]]
            if not stmts:
                raise AnalysisError(409, "The selected filters match no distribution lines")
        a = paper.analyze_paper(stmts, params, service.pages_by_month(session), filtered=bool(want_m or want_u))
        full = [s for s in service.load_paper(session, pid)]
        dims = [{"key": "months", "param": "month", "label": p.t("f_months"), "searchable": False,
                 "items": [{"id": m, "label": report.period_label(lang, (int(m[:4]), int(m[5:])))} for m in months]},
                {"key": "branches", "param": "branch", "label": p.t("f_branches"), "searchable": True,
                 "items": sorted(({"id": k, "label": v} for k, v in units.items()), key=lambda i: i["label"])}]
        rm = paper_report.build_paper_report(a, stmts, lang, origin, filters, dims, bool(service.pages_by_month(session)))
        a["origin"] = origin
        a["statements"] = [{"po_no": s["po_no"], "file_name": s["file_name"], "rows": len(s["rows"])} for s in full]
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
        if "by_month" in a:
            return {"paper": {"totals": a["totals"], "by_month": a["by_month"], "head_office": [{k: v for k, v in u.items() if k not in ("by_month", "flags")} for u in a["head_office"]],
                              "hq_summary": a["hq_summary"], "params": a["params"], "origin": a.get("origin"), "statements": a.get("statements")}}
        rec = a.get("reconciliation")
        return {"totals": a["totals"], "by_class": a["by_class"], "by_location": a["by_location"], "bands": a["bands"],
                "reconciliation": rec, "unsupported": a["unsupported"], "thresholds": a["thresholds"], "thresholds_origin": a["thresholds_origin"]}
