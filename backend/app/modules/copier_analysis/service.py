"""Upload -> validate -> store for the copier module. A *cycle* is one month: the statement, its supplier invoice,
the Word statement and the scanned status pages of that month are attached to it. Files are stored untouched."""
import hashlib
import re
from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.analysis import AnalysisError
from app.core.entities import EntityResolver
from app.models import (
    AnalysisCycle, AnalysisDataset, CopierEvidence, CopierInvoice, CopierInvoiceLine, CopierMachine, CopierPaperRow,
)
from app.modules.copier_analysis import evidence as ev
from app.modules.copier_analysis import invoice as inv_mod
from app.modules.copier_analysis import paper as paper_mod
from app.modules.copier_analysis import statement as st_mod

MODULE_ID = "copier_analysis"
_PREFIX = re.compile(r"^\s*تأجير ماكينات تصوير مستندات\s*/?\s*")


def _store(content: bytes, filename: str) -> tuple[str, str]:
    digest = hashlib.sha256(content).hexdigest()
    d = Path(get_settings().upload_dir) / MODULE_ID
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{digest[:16]}{Path(filename).suffix.lower()}"
    path.write_bytes(content)
    return digest, str(path)


def _duplicate(session: Session, digest: str) -> None:
    dup = session.scalar(select(AnalysisDataset).where(AnalysisDataset.module_id == MODULE_ID, AnalysisDataset.file_hash == digest))
    if dup:
        raise AnalysisError(409, {"message": f"This exact file was already uploaded (dataset {dup.id})",
                                  "dataset_id": dup.cycle_id or dup.id})


def get_cycle(session: Session, period: tuple[int, int], create: bool = True) -> AnalysisCycle | None:
    c = session.scalar(select(AnalysisCycle).where(AnalysisCycle.module_id == MODULE_ID, AnalysisCycle.period_year == period[0],
                                                   AnalysisCycle.period_month == period[1]))
    if c is None and create:
        c = AnalysisCycle(module_id=MODULE_ID, period_year=period[0], period_month=period[1], label=f"{period[0]}-{period[1]:02d}")
        session.add(c)
        session.flush()
    return c


def _role_exists(session: Session, cycle_id: int, role: str) -> AnalysisDataset | None:
    return session.scalar(select(AnalysisDataset).where(AnalysisDataset.cycle_id == cycle_id, AnalysisDataset.role == role))


def _issues(items) -> list[dict]:
    return [{"code": i.code, "severity": i.severity, "message": i.message, "count": i.count, "examples": i.examples} for i in items]


def _need_period(options: dict, found: tuple[int, int] | None, what: str) -> tuple[int, int]:
    if found:
        return found
    if options.get("year") and options.get("month"):
        return int(options["year"]), int(options["month"])
    raise AnalysisError(422, f"The {what} does not state its period; upload again with the year and month")


# ------------------------------------------------------------------------------------------------ ingest
def ingest(session: Session, content: bytes, filename: str, user: str | None, options: dict):
    name = filename.lower()
    if name.endswith((".xlsx", ".xlsm")):
        if paper_mod.is_distribution_workbook(content):
            return _ingest_paper(session, content, filename, user, options)
        return _ingest_statement(session, content, filename, user, options)
    if name.endswith((".doc", ".docx")):
        return _ingest_word(session, content, filename, user, options)
    if name.endswith(".pdf"):
        try:
            return _ingest_invoice(session, content, filename, user, options)
        except inv_mod.UnrecognisedInvoice:
            return _ingest_evidence(session, content, filename, user, options)
    raise AnalysisError(400, "Supported files: the monthly Excel statement, the Word statement, the supplier e-invoice PDF, scanned status-page PDF")


def _ingest_statement(session, content, filename, user, options):
    digest, path = _store(content, filename)
    _duplicate(session, digest)
    try:
        st = st_mod.parse_statement_xlsx(content)
    except st_mod.UnrecognisedStatement as exc:
        raise AnalysisError(422, str(exc)) from exc
    except Exception as exc:
        if exc.__class__.__name__ in ("BadZipFile", "InvalidFileException"):
            raise AnalysisError(400, "The file is not a readable Excel workbook") from exc
        raise
    period = _need_period(options, st.period, "statement")
    cycle = get_cycle(session, period)
    if _role_exists(session, cycle.id, "statement"):
        raise AnalysisError(409, {"message": "This period already has a consumption statement; delete it first to replace it",
                                  "dataset_id": cycle.id})
    st_mod.validate_machines(st)
    if st.details:
        st_mod.match_details(st, st.details, "xlsx_part2")
    resolver = EntityResolver(session, {"branch": "review"})
    resolved: dict[str, int | None] = {}
    unresolved = []
    ds = AnalysisDataset(module_id=MODULE_ID, layout="copier_statement", scope_label="copier_statement", file_name=Path(filename).name,
                         file_hash=digest, storage_path=path, title=st.title, period_year=period[0], year_source="file" if st.period else "uploader",
                         facts_count=len(st.machines), created_by=user, cycle_id=cycle.id, role="statement", status="ready")
    session.add(ds)
    session.flush()
    for m in st.machines:
        bid = None
        if m.branch_key not in resolved:
            res = resolver.resolve("branch", st_mod.display_branch(m.branch_source))
            resolved[m.branch_key] = res.entity_id if res is not None and res.status == "resolved" else None
            if resolved[m.branch_key] is None:
                unresolved.append(st_mod.display_branch(m.branch_source))
        bid = resolved[m.branch_key]
        session.add(CopierMachine(
            dataset_id=ds.id, source_ref=m.source_ref, class_key=m.class_key, package=m.package, branch_source=m.branch_source,
            branch_display=st_mod.display_branch(m.branch_source), branch_key=f"branch:{bid}" if bid else m.branch_key, branch_id=bid,
            seq=m.seq, prev_reading=m.prev, cur_reading=m.cur, consumption=m.cons, excess_stated=m.exc, location_group=m.location_group,
            group_kind=m.group_kind, rent_detail=m.rent_detail, detail_sources=m.detail_sources, flags=m.flags))
    if unresolved:
        st.issue("branch_not_in_master", "info", "Branch names not found in the branch master (reported as written in the file)")
        st.issues[-1].count = len(set(unresolved))
        st.issues[-1].examples = sorted(set(unresolved))[:8]
    ds.summary = {"period": list(period), "issues": _issues(st.issues),
                  "blocks": [{"class_key": b.class_key, "title": b.title, "machines": b.machines, "stated_excess_total": b.stated_excess_total,
                              "computed_excess": b.computed_excess} for b in st.blocks],
                  "part2_rows": len(st.details)}
    session.commit()
    _refresh_cycle(session, cycle.id)
    return _result(session, cycle, ds)


def _ingest_paper(session, content, filename, user, options):
    """Paper distribution statement of one purchase order. It spans several months, so it belongs to no cycle."""
    digest, path = _store(content, filename)
    _duplicate(session, digest)
    try:
        st = paper_mod.parse_distribution_xlsx(content)
    except paper_mod.UnrecognisedPaperStatement as exc:
        raise AnalysisError(422, str(exc)) from exc
    if st.po_no:
        for d in session.scalars(select(AnalysisDataset).where(AnalysisDataset.module_id == MODULE_ID, AnalysisDataset.role == "paper_distribution")):
            if (d.summary or {}).get("po_no") == st.po_no:
                raise AnalysisError(409, {"message": f"A distribution statement for purchase order {st.po_no} already exists; delete it first to replace it",
                                          "dataset_id": f"paper:{d.id}"})
    dates = [r.distributed_on for r in st.rows if r.distributed_on]
    ds = AnalysisDataset(module_id=MODULE_ID, layout="copier_paper_distribution", scope_label="paper_distribution", file_name=Path(filename).name,
                         file_hash=digest, storage_path=path, title=st.title, period_year=min(dates).year if dates else None, year_source="file",
                         period_from=min(dates) if dates else None, period_to=max(dates) if dates else None, facts_count=len(st.rows),
                         created_by=user, role="paper_distribution", status="ready")
    session.add(ds)
    session.flush()
    for r in st.rows:
        session.add(CopierPaperRow(dataset_id=ds.id, source_ref=r.source_ref, seq=r.seq, cartons=r.cartons, branch_source=r.branch_source,
                                   branch_display=r.branch_display, branch_key=r.branch_key, is_head_office=r.is_head_office,
                                   department=r.department, distributed_on=r.distributed_on, flags=r.flags))
    ds.summary = {"po_no": st.po_no, "receipt_date": st.receipt_date.isoformat() if st.receipt_date else None,
                  "received_cartons": str(st.received_cartons) if st.received_cartons is not None else None,
                  "stated_total": str(st.stated_total) if st.stated_total is not None else None,
                  "stated_months": {str(k): str(v) for k, v in st.stated_months.items()}, "issues": _issues(st.issues)}
    session.commit()
    from app.core.analysis import UploadResult
    return UploadResult("paper", {"module": "copiers", "label": f"paper PO {st.po_no or ''}".strip(),
                                  "uploaded": {"dataset_id": ds.id, "role": ds.role, "file_name": ds.file_name, "status": ds.status, "rows": len(st.rows)}}, 201)


def _ingest_word(session, content, filename, user, options):
    digest, path = _store(content, filename)
    _duplicate(session, digest)
    try:
        rows = st_mod.parse_statement_word(content, filename)
    except Exception as exc:
        raise AnalysisError(422, f"The Word file could not be read as a consumption statement: {exc}") from exc
    if not rows:
        raise AnalysisError(422, "No consumption table found in the Word file")
    title = _word_title(content, filename)
    period = _need_period(options, st_mod._period(title or ""), "Word statement")
    cycle = get_cycle(session, period)
    if _role_exists(session, cycle.id, "statement_word"):
        raise AnalysisError(409, {"message": "This period already has a Word statement; delete it first to replace it", "dataset_id": cycle.id})
    ds = AnalysisDataset(module_id=MODULE_ID, layout="copier_statement_word", scope_label="copier_statement_detail", file_name=Path(filename).name,
                         file_hash=digest, storage_path=path, title=title, period_year=period[0], year_source="file", facts_count=len(rows),
                         created_by=user, cycle_id=cycle.id, role="statement_word", status="ready")
    session.add(ds)
    session.flush()
    ds.summary = {"period": list(period), "rows": len(rows), "issues": []}
    session.commit()
    _refresh_cycle(session, cycle.id)
    return _result(session, cycle, ds)


def _word_title(content: bytes, filename: str) -> str | None:
    try:
        if filename.lower().endswith(".docx") or content[:2] == b"PK":
            import io

            from docx import Document
            return next((p.text for p in Document(io.BytesIO(content)).paragraphs if p.text.strip()), None)
        from app.core.extraction.doc_legacy import read_doc_text
        return next((p for p in read_doc_text(content).split("\r") if p.strip()), None)
    except Exception:
        return None


def _ingest_invoice(session, content, filename, user, options):
    inv = inv_mod.parse_invoice(content)  # raises UnrecognisedInvoice for evidence/scans
    digest, path = _store(content, filename)
    _duplicate(session, digest)
    period = _need_period(options, inv.period, "invoice")
    cycle = get_cycle(session, period)
    if _role_exists(session, cycle.id, "invoice"):
        raise AnalysisError(409, {"message": "This period already has a supplier invoice; delete it first to replace it", "dataset_id": cycle.id})
    ds = AnalysisDataset(module_id=MODULE_ID, layout="copier_invoice", scope_label="supplier_invoice", file_name=Path(filename).name,
                         file_hash=digest, storage_path=path, title=f"e-invoice {inv.internal_no or ''}".strip(), period_year=period[0],
                         year_source="file", facts_count=len(inv.lines), created_by=user, cycle_id=cycle.id, role="invoice", status="ready")
    session.add(ds)
    session.flush()
    row = CopierInvoice(dataset_id=ds.id, internal_no=inv.internal_no, electronic_id=inv.electronic_id, issued_on=inv.issued_on, status=inv.status,
                        seller_reg=inv.seller_reg, buyer_reg=inv.buyer_reg, seller_name=inv.seller_name, buyer_name=inv.buyer_name,
                        totals={k: str(v) for k, v in inv.totals.items()}, issues=inv.issues)
    session.add(row)
    session.flush()
    for ln in inv.lines:
        session.add(CopierInvoiceLine(invoice_id=row.id, line_no=ln.line_no, page=ln.page, description=ln.description, kind=ln.kind,
                                      packages=ln.packages, color=ln.color, a3=ln.a3, printers=ln.printers, qty=ln.qty, unit_price=ln.unit_price,
                                      sales_total=ln.sales_total, net_total=ln.net_total, vat_value=ln.vat_value, vat_rate=ln.vat_rate,
                                      wht_value=ln.wht_value, wht_rate=ln.wht_rate, total=ln.total, period_from=ln.period_from,
                                      period_to=ln.period_to, flags=ln.flags))
    ds.summary = {"period": list(period), "issues": [{"code": "line_flag", "severity": "info", "message": f"line {ln.line_no}: {', '.join(ln.flags)}",
                                                      "count": 1, "examples": []} for ln in inv.lines if ln.flags]}
    session.commit()
    return _result(session, cycle, ds)


def _ingest_evidence(session, content, filename, user, options):
    digest, path = _store(content, filename)
    _duplicate(session, digest)
    period = None
    if options.get("year") and options.get("month"):
        period = (int(options["year"]), int(options["month"]))
    if period is None:  # the pages carry their own print timestamps; fall back to the most recent cycle
        last = session.scalar(select(AnalysisCycle).where(AnalysisCycle.module_id == MODULE_ID).order_by(
            AnalysisCycle.period_year.desc(), AnalysisCycle.period_month.desc()))
        if last is None:
            raise AnalysisError(422, "Upload the monthly statement first (or state the year and month): the scanned pages are evidence for a period")
        period = (last.period_year, last.period_month)
    cycle = get_cycle(session, period)
    ds = AnalysisDataset(module_id=MODULE_ID, layout="copier_evidence", scope_label="evidence_only", file_name=Path(filename).name,
                         file_hash=digest, storage_path=path, title="status pages (evidence)", period_year=period[0], year_source="uploader",
                         facts_count=0, created_by=user, cycle_id=cycle.id, role="evidence", status="processing", summary={"period": list(period)})
    session.add(ds)
    session.commit()
    ds_id = ds.id

    def background():
        from sqlalchemy.orm import Session as S

        from app.db import get_engine
        with S(get_engine()) as s:
            process_evidence(s, ds_id)
    return _result(session, cycle, ds, status=202, background=background)


def process_evidence(session: Session, dataset_id: int) -> None:
    ds = session.get(AnalysisDataset, dataset_id)
    try:
        pages = ev.read_pdf(Path(ds.storage_path))
    except Exception as exc:  # OCR must never take the module down
        ds.status, ds.summary = "failed", {**(ds.summary or {}), "error": str(exc)[:300]}
        session.commit()
        return
    session.execute(delete(CopierEvidence).where(CopierEvidence.dataset_id == ds.id))
    for p in pages:
        session.add(CopierEvidence(dataset_id=ds.id, page_no=p.page_no, counter_value=p.counter_value, counter_raw=p.counter_raw,
                                   printed_at_text=p.printed_at_text, confidence=p.confidence))
    ds.facts_count, ds.status = len(pages), "ready"
    session.commit()
    _refresh_cycle(session, ds.cycle_id)


def _refresh_cycle(session: Session, cycle_id: int) -> None:
    """Re-run the supporting comparisons whenever a file of the cycle changes (order of upload does not matter)."""
    stmt = _role_exists(session, cycle_id, "statement")
    if stmt is None:
        return
    machines = session.scalars(select(CopierMachine).where(CopierMachine.dataset_id == stmt.id)).all()
    # Word statement (supporting): detail by readings
    word = _role_exists(session, cycle_id, "statement_word")
    if word is not None:
        rows = st_mod.parse_statement_word(Path(word.storage_path).read_bytes(), word.file_name)
        st = st_mod.Statement()
        for m in machines:
            st.machines.append(st_mod.Machine(m.source_ref, m.class_key, m.package, m.branch_source, m.branch_key, m.seq, m.prev_reading,
                                              m.cur_reading, m.consumption, m.excess_stated, location_group=m.location_group,
                                              group_kind=m.group_kind, detail_sources=[s for s in (m.detail_sources or []) if s != "word"]))
        st_mod.match_details(st, rows, "word")
        for dbm, m in zip(machines, st.machines):
            dbm.detail_sources = m.detail_sources
            if dbm.location_group is None and m.location_group:
                dbm.location_group, dbm.group_kind = m.location_group, m.group_kind
        word.summary = {**(word.summary or {}), "issues": _issues(st.issues)}
    # evidence (supporting): counters vs current readings
    evd = _role_exists(session, cycle_id, "evidence")
    if evd is not None and evd.status == "ready":
        pages = session.scalars(select(CopierEvidence).where(CopierEvidence.dataset_id == evd.id)).all()
        res = ev.match_pages([{"page_no": p.page_no, "counter_value": p.counter_value} for p in pages],
                             [{"source_ref": m.source_ref, "cur": m.cur_reading} for m in machines])
        for p, r in zip(pages, res):
            p.status, p.matched_machine_ref, p.note = r["status"], r["matched_machine_ref"], r["note"]
    session.commit()


def _result(session, cycle, ds, status: int = 201, background=None):
    from app.core.analysis import UploadResult
    return UploadResult(cycle.id, {**cycle_meta(session, cycle), "uploaded": {"dataset_id": ds.id, "role": ds.role, "file_name": ds.file_name,
                                                                              "status": ds.status}}, status, background)


# ------------------------------------------------------------------------------------------------ queries
def cycle_meta(session: Session, cycle: AnalysisCycle) -> dict:
    dss = session.scalars(select(AnalysisDataset).where(AnalysisDataset.cycle_id == cycle.id).order_by(AnalysisDataset.id)).all()
    machines = sum(d.facts_count for d in dss if d.role == "statement")
    issues = [i for d in dss for i in (d.summary or {}).get("issues", [])]
    return {"id": cycle.id, "module": "copiers", "period": [cycle.period_year, cycle.period_month], "label": cycle.label,
            "sources": [{"dataset_id": d.id, "role": d.role, "file_name": d.file_name, "status": d.status, "rows": d.facts_count} for d in dss],
            "machines": machines, "has_statement": any(d.role == "statement" for d in dss), "has_invoice": any(d.role == "invoice" for d in dss),
            "issues": issues, "status": "processing" if any(d.status == "processing" for d in dss) else "ready"}


def load_machines(session: Session, cycle_id: int) -> list[dict]:
    stmt = _role_exists(session, cycle_id, "statement")
    if stmt is None:
        return []
    rows = session.scalars(select(CopierMachine).where(CopierMachine.dataset_id == stmt.id)).all()
    return [{"id": r.id, "source_ref": r.source_ref, "class_key": r.class_key, "package": r.package, "branch_source": r.branch_source,
             "branch_display": r.branch_display, "branch_key": r.branch_key, "location_group": r.location_group, "group_kind": r.group_kind,
             "cons": r.consumption, "exc": r.excess_stated, "prev": r.prev_reading, "cur": r.cur_reading, "rent_detail": r.rent_detail,
             "detail_sources": r.detail_sources or [], "flags": r.flags or []} for r in rows]


def load_invoice(session: Session, cycle_id: int) -> dict | None:
    ds = _role_exists(session, cycle_id, "invoice")
    if ds is None:
        return None
    inv = session.scalar(select(CopierInvoice).where(CopierInvoice.dataset_id == ds.id))
    lines = session.scalars(select(CopierInvoiceLine).where(CopierInvoiceLine.invoice_id == inv.id).order_by(CopierInvoiceLine.line_no)).all()
    return {"internal_no": inv.internal_no, "electronic_id": inv.electronic_id, "issued_on": inv.issued_on, "status": inv.status,
            "seller_reg": inv.seller_reg, "buyer_reg": inv.buyer_reg, "seller_name": inv.seller_name, "buyer_name": inv.buyer_name,
            "totals": {k: Decimal(v) for k, v in (inv.totals or {}).items()}, "file_name": ds.file_name,
            "lines": [{"line_no": ln.line_no, "page": ln.page, "description": ln.description,
                       "description_short": _PREFIX.sub("", ln.description)[:70], "kind": ln.kind, "packages": ln.packages or [],
                       "color": ln.color, "a3": ln.a3, "printers": ln.printers, "qty": ln.qty, "unit_price": ln.unit_price,
                       "sales_total": ln.sales_total, "total": ln.total, "vat_rate": ln.vat_rate, "wht_rate": ln.wht_rate, "flags": ln.flags or []}
                      for ln in lines]}


def load_evidence(session: Session, cycle_id: int) -> dict | None:
    ds = _role_exists(session, cycle_id, "evidence")
    if ds is None:
        return None
    rows = session.scalars(select(CopierEvidence).where(CopierEvidence.dataset_id == ds.id).order_by(CopierEvidence.page_no)).all()
    return {"file_name": ds.file_name, "status": ds.status, "error": (ds.summary or {}).get("error"),
            "pages": [{"page_no": r.page_no, "counter": r.counter_value, "printed_at": r.printed_at_text, "status": r.status,
                       "machine": r.matched_machine_ref, "note": r.note} for r in rows]}


def cycle_sources_issues(session: Session, cycle_id: int) -> list[dict]:
    return [i for d in session.scalars(select(AnalysisDataset).where(AnalysisDataset.cycle_id == cycle_id)).all()
            for i in (d.summary or {}).get("issues", [])]


def delete_cycle(session: Session, cycle_id: int) -> None:
    for d in session.scalars(select(AnalysisDataset).where(AnalysisDataset.cycle_id == cycle_id)).all():
        session.execute(delete(CopierMachine).where(CopierMachine.dataset_id == d.id))
        session.execute(delete(CopierEvidence).where(CopierEvidence.dataset_id == d.id))
        for inv in session.scalars(select(CopierInvoice).where(CopierInvoice.dataset_id == d.id)).all():
            session.execute(delete(CopierInvoiceLine).where(CopierInvoiceLine.invoice_id == inv.id))
            session.delete(inv)
        session.delete(d)
    session.execute(delete(AnalysisCycle).where(AnalysisCycle.id == cycle_id))
    session.commit()



# ------------------------------------------------------------------------------------------------ paper
def paper_datasets(session: Session, only: int | None = None) -> list[AnalysisDataset]:
    q = select(AnalysisDataset).where(AnalysisDataset.module_id == MODULE_ID, AnalysisDataset.role == "paper_distribution").order_by(
        AnalysisDataset.period_from, AnalysisDataset.id)
    if only is not None:
        q = q.where(AnalysisDataset.id == only)
    return list(session.scalars(q).all())


def load_paper(session: Session, only: int | None = None) -> list[dict]:
    out = []
    for d in paper_datasets(session, only):
        rows = session.scalars(select(CopierPaperRow).where(CopierPaperRow.dataset_id == d.id).order_by(CopierPaperRow.id)).all()
        sm = d.summary or {}
        out.append({"dataset_id": d.id, "file_name": d.file_name, "po_no": sm.get("po_no"),
                    "receipt_date": date.fromisoformat(sm["receipt_date"]) if sm.get("receipt_date") else None,
                    "received_cartons": Decimal(sm["received_cartons"]) if sm.get("received_cartons") else None,
                    "stated_total": Decimal(sm["stated_total"]) if sm.get("stated_total") else None, "issues": sm.get("issues", []),
                    "rows": [{"source_ref": r.source_ref, "cartons": r.cartons, "branch_display": r.branch_display, "branch_key": r.branch_key,
                              "is_head_office": r.is_head_office, "department": r.department, "distributed_on": r.distributed_on,
                              "flags": r.flags or []} for r in rows]})
    return out


def pages_by_month(session: Session) -> dict[tuple[int, int], dict]:
    """Pages per month (and per branch, by normalised name) from the monthly consumption statements: the machines' side of the comparison."""
    out: dict[tuple[int, int], dict] = {}
    for c in session.scalars(select(AnalysisCycle).where(AnalysisCycle.module_id == MODULE_ID)).all():
        machines = load_machines(session, c.id)
        if not machines:
            continue
        by_branch: dict[str, int] = {}
        for m in machines:
            k = st_mod.branch_key(m["branch_display"])
            by_branch[k] = by_branch.get(k, 0) + (m["cons"] or 0)
        out[(c.period_year, c.period_month)] = {"pages": sum(by_branch.values()), "by_branch": by_branch}
    return out


def delete_paper(session: Session, only: int | None = None) -> None:
    for d in paper_datasets(session, only):
        session.execute(delete(CopierPaperRow).where(CopierPaperRow.dataset_id == d.id))
        session.delete(d)
    session.commit()
