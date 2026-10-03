"""Aramex analytics as an analysis-module adapter. Items: "all" (every complete invoice), "m:YYYY-MM" (one month, compared with the
previous month) and "inv:<id>" (one invoice, with its reconciliation)."""
from app.core.analysis import AnalysisError, ModuleInfo
from app.core.settings_store import effective_struct, effective_thresholds
from app.modules.aramex_analysis import allocation, engine, report, service


def _parse(item_id) -> tuple[str, object]:
    s = str(item_id)
    if s == "all":
        return "all", None
    if s.startswith("m:"):
        try:
            y, m = s[2:].split("-")
            return "month", (int(y), int(m))
        except ValueError:
            pass
    if s.startswith("inv:") and s[4:].isdigit():
        return "inv", int(s[4:])
    raise AnalysisError(404, "Item not found")


class AramexAdapter:
    info = ModuleInfo(
        key="aramex", module_id="aramex_analysis", label={"ar": "شحنات Aramex", "en": "Aramex shipments"},
        accepts=(".xlsx", ".xlsm", ".pdf"), filters={"branches": "branch", "services": "service", "cities": "city"},
        upload_hint={"ar": "فاتورة Aramex الإلكترونية (PDF) وكشف الشحنات (Excel) معًا لكل فاتورة؛ وملحق العقد الممسوح مرجع فقط",
                     "en": "The Aramex e-invoice (PDF) and its shipment sheet (Excel) together for each invoice; the scanned contract appendix is reference only"},
        thresholds_key="aramex.thresholds")

    def ingest(self, session, content, filename, user, options):
        return service.ingest(session, content, filename, user, options)

    # ------------------------------------------------------------------------------------------ items
    def list_items(self, session) -> list[dict]:
        invs = service.invoices(session)
        if not invs:
            return []
        rules = allocation.rules_from(effective_struct(session, "aramex.parties")[0])
        rows, _exc, _info = service.load_analysis_rows(session, rules)
        out = []
        if rows:
            out.append({"id": "all", "label": "Σ " + ", ".join(i.invoice_no or i.bill_doc for i in invs if i.pdf_dataset_id and i.xlsx_dataset_id), "layout_label": "all"})
            cov = (min(r["pickup_on"] for r in rows), max(r["pickup_on"] for r in rows))
            for m in sorted(engine.months_table(rows, cov), key=lambda m: m["period"], reverse=True):
                y, mo = m["period"]
                out.append({"id": f"m:{y}-{mo:02d}", "label": f"{y}-{mo:02d} · {m['n']}" + (" · partial" if m["partial"] else ""), "layout_label": "month", "period": [y, mo]})
        for i in reversed(invs):
            meta = service.invoice_meta(session, i)
            out.append({"id": meta["id"], "label": f"{meta['label']} · " + ("PDF+Excel" if meta["status"] == "ready" else "incomplete: " + ("needs Excel" if meta["has_pdf"] else "needs PDF")),
                        "status": meta["status"], "layout_label": "invoice"})
        return out

    def item_meta(self, session, item_id, admin) -> dict:
        kind, v = _parse(item_id)
        invs = service.invoices(session)
        if kind == "inv":
            inv = next((i for i in invs if i.id == v), None)
            if inv is None:
                raise AnalysisError(404, "Invoice not found")
            return service.invoice_meta(session, inv)
        return {"id": str(item_id), "module": "aramex", "invoices": [service.invoice_meta(session, i) for i in invs], "status": "ready"}

    def delete_item(self, session, item_id) -> None:
        kind, v = _parse(item_id)
        if kind != "inv":
            raise AnalysisError(409, "Delete an invoice (inv:<id>); months and the total are views over the uploaded invoices")
        if session.get(service.AramexInvoice, v) is None:
            raise AnalysisError(404, "Invoice not found")
        service.delete_invoice(session, v)

    # ------------------------------------------------------------------------------------------ build
    def build(self, session, item_id, lang, admin, filters):
        kind, v = _parse(item_id)
        th, th_origin = effective_thresholds(session, "aramex")
        pcfg, porigin = effective_struct(session, "aramex.parties")
        rates, _ro = effective_struct(session, "aramex.rates")
        rows, merge_exc, info = service.load_analysis_rows(session, allocation.rules_from(pcfg))
        if not rows:
            raise AnalysisError(409, "No complete invoice yet: upload an invoice's PDF and its Excel sheet")
        c = report.C(lang)
        filters = {k: x for k, x in (filters or {}).items() if x}
        labels: dict[str, str] = {}
        for r in rows:
            for side in ("sender", "receiver"):
                p = r[side]
                labels.setdefault(p["key"], c.t("hq") if p["kind"] == "head_office" else c.t("unalloc") if p["kind"] == "unallocated" else p["display"])
        dims = [{"key": "branches", "param": "branch", "label": c.t("f_branches"), "searchable": True,
                 "items": sorted(({"id": k, "label": n} for k, n in labels.items()), key=lambda i: i["label"])},
                {"key": "services", "param": "service", "label": c.t("f_services"), "searchable": False, "items": [{"id": s, "label": s} for s in sorted({r["product"] or "—" for r in rows})]},
                {"key": "cities", "param": "city", "label": c.t("f_cities"), "searchable": True,
                 "items": [{"id": s, "label": s} for s in sorted({x for r in rows for x in (r["origin"], r["destination"]) if x})]}]
        coverage = (min(r["pickup_on"] for r in rows), max(r["pickup_on"] for r in rows))
        allf = rows
        if filters.get("branches"):
            ks = set(filters["branches"])
            allf = [r for r in allf if r["sender"]["key"] in ks or r["receiver"]["key"] in ks]
        if filters.get("services"):
            allf = [r for r in allf if (r["product"] or "—") in set(filters["services"])]
        if filters.get("cities"):
            cs = set(filters["cities"])
            allf = [r for r in allf if r["origin"] in cs or r["destination"] in cs]
        month = None
        if kind == "month":
            month = v
            scope_rows = [r for r in allf if engine.month_of(r) == v]
            scope = {"kind": "month", "month": v}
        elif kind == "inv":
            if v not in info:
                raise AnalysisError(409, "This invoice is incomplete: upload both its PDF and its Excel sheet")
            scope_rows = [r for r in allf if r["invoice_id"] == v]
            scope = {"kind": "inv", "label": info[v]["invoice_no"] or info[v]["bill_doc"]}
        else:
            scope_rows, scope = allf, {"kind": "all"}
        if kind == "month" and not any(engine.month_of(r) == v for r in rows):
            raise AnalysisError(404, "No shipments in this month")
        if not scope_rows and not filters:
            raise AnalysisError(409, "No shipments in this scope")
        if not scope_rows:
            raise AnalysisError(409, "The selected filters match no shipments")
        filtered = bool(filters)
        a = engine.analyze(allf, scope_rows, th, rates, month, coverage, filtered)
        ids = sorted({r["invoice_id"] for r in scope_rows})
        invs = [info[i] for i in ids]
        recons = {} if filtered else {i: service.reconcile_invoice(session, i, th["reconcile_tolerance"]) for i in ids}
        exc = [e for e in merge_exc if e["invoice_id"] in ids]
        datasets = [d for i in ids for d in self._datasets(session, i)]
        issues = [x for d in datasets for x in (d.summary or {}).get("issues", [])]
        refs = service.reference_documents(session)
        sources = [{"role": d.role, "file_name": d.file_name, "rows": d.facts_count} for d in datasets] + [{"role": d.role, "file_name": d.file_name, "rows": 0} for d in refs]
        unsupported = ["governorate", "zone", "budget"] + ([] if rates.get("first_kg") and rates.get("additional_kg") else ["rates"]) + (
            ["prev"] if kind == "month" and not a["mom"]["prev_available"] else [])
        note = {"locations": len(pcfg["head_office_locations"]), "contacts": len(pcfg["head_office_contacts"]), "reference_docs": len(refs),
                "origin": "custom" if any(o == "custom" for o in porigin.values()) else "default"}
        rm = report.build_report(scope, a, invs, recons, exc, issues, sources, th, th_origin, note, unsupported, lang, filters, dims)
        a["recons"] = recons
        return rm, a

    @staticmethod
    def _datasets(session, invoice_id):
        inv = session.get(service.AramexInvoice, invoice_id)
        return [session.get(service.AnalysisDataset, i) for i in (inv.pdf_dataset_id, inv.xlsx_dataset_id) if i]

    def api_analysis(self, a: dict) -> dict:
        return {"totals": a["totals"], "parties": a["parties"], "controls": a["controls"], "allocation": a["allocation"], "months": a["months"],
                "mom": a.get("mom"), "thresholds": a["thresholds"],
                "reconciliation": {str(k): v["summary"] for k, v in (a.get("recons") or {}).items()}}

