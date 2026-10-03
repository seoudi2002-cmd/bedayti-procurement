"""Upload -> validate -> store for the Aramex module. One *invoice* (bill document) = its PDF (dates, products, totals) + its
Excel (parties, weights); either may arrive first. A scanned contract appendix is stored as a reference document only.
Files are stored untouched; shipments are stored as each source states them and merged by AWB only when analysed."""
import hashlib
from decimal import Decimal
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.analysis import AnalysisError, UploadResult
from app.core.cleaning.normalizers import normalize_text
from app.core.entities import EntityResolver
from app.models import AnalysisDataset, AramexInvoice, AramexShipment, DimBranch
from app.modules.aramex_analysis import allocation, engine
from app.modules.aramex_analysis import invoice as pdf_mod
from app.modules.aramex_analysis import shipments as xl_mod

MODULE_ID = "aramex_analysis"


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
        raise AnalysisError(409, {"message": f"This exact file was already uploaded (dataset {dup.id})", "dataset_id": dup.id})


def _issues(items) -> list[dict]:
    return [{"code": i.code, "severity": i.severity, "message": i.message, "count": i.count, "examples": i.examples} for i in items]


def _invoice(session: Session, bill_doc: str) -> AramexInvoice:
    inv = session.scalar(select(AramexInvoice).where(AramexInvoice.bill_doc == bill_doc))
    if inv is None:
        inv = AramexInvoice(bill_doc=bill_doc)
        session.add(inv)
        session.flush()
    return inv


def _s(d: dict) -> dict:
    return {k: str(v) for k, v in d.items()}


# ------------------------------------------------------------------------------------------------ ingest
def ingest(session: Session, content: bytes, filename: str, user: str | None, options: dict) -> UploadResult:
    name = filename.lower()
    if name.endswith((".xlsx", ".xlsm")):
        if not xl_mod.is_shipments_workbook(content):
            raise AnalysisError(422, "Not an Aramex shipment detail sheet (no 'Airway Bill No.' column)")
        return _ingest_xlsx(session, content, filename, user)
    if name.endswith(".pdf"):
        try:
            return _ingest_pdf(session, content, filename, user)
        except pdf_mod.UnrecognisedInvoice as exc:
            if pdf_mod.has_text(content):
                raise AnalysisError(422, str(exc)) from exc
            return _ingest_reference(session, content, filename, user)
    raise AnalysisError(400, "Supported files: the Aramex e-invoice PDF, its shipment detail Excel, and the scanned contract appendix (PDF, reference only)")


def _ingest_pdf(session, content, filename, user):
    inv = pdf_mod.parse_invoice(content)
    if not inv.bill_doc:
        raise AnalysisError(422, "The invoice number could not be read from the PDF")
    digest, path = _store(content, filename)
    _duplicate(session, digest)
    row = _invoice(session, inv.bill_doc)
    if row.pdf_dataset_id:
        raise AnalysisError(409, {"message": "This invoice already has its PDF; delete the invoice first to replace it", "dataset_id": f"inv:{row.id}"})
    days = [s.pickup_on for s in inv.shipments]
    ds = AnalysisDataset(module_id=MODULE_ID, layout="aramex_invoice_pdf", scope_label="invoice", file_name=Path(filename).name, file_hash=digest,
                         storage_path=path, title=inv.invoice_no, period_year=min(days).year, year_source="file", period_from=min(days), period_to=max(days),
                         facts_count=len(inv.shipments), created_by=user, role="invoice_pdf", status="ready")
    session.add(ds)
    session.flush()
    row.invoice_no, row.doc_date, row.due_date, row.customer_no, row.currency = inv.invoice_no, inv.doc_date, inv.due_date, inv.customer_no, inv.currency
    row.pdf_dataset_id, row.pdf_totals = ds.id, _s(inv.totals)
    for s in inv.shipments:
        session.add(AramexShipment(invoice_id=row.id, source="pdf", awb=s.awb, seq=s.seq, pickup_on=s.pickup_on, route_text=s.route_text, product=s.product,
                                   pcs=s.pcs, weight=s.weight, base=s.base, other=s.other, net=s.net))
    ds.summary = {"bill_doc": inv.bill_doc, "invoice_no": inv.invoice_no, "pages": inv.pages, "issues": _issues(inv.issues)}
    session.commit()
    return _result(session, row, ds)


def _ingest_xlsx(session, content, filename, user):
    try:
        x = xl_mod.parse_shipments_xlsx(content)
    except xl_mod.UnrecognisedShipments as exc:
        raise AnalysisError(422, str(exc)) from exc
    if not x.bill_doc:
        raise AnalysisError(422, "The sheet does not state its invoice (Bill. Doc.); it cannot be linked to an invoice")
    digest, path = _store(content, filename)
    _duplicate(session, digest)
    row = _invoice(session, x.bill_doc)
    if row.xlsx_dataset_id:
        raise AnalysisError(409, {"message": "This invoice already has its Excel sheet; delete the invoice first to replace it", "dataset_id": f"inv:{row.id}"})
    ds = AnalysisDataset(module_id=MODULE_ID, layout="aramex_shipments_xlsx", scope_label="invoice", file_name=Path(filename).name, file_hash=digest,
                         storage_path=path, title=f"shipments {x.bill_doc}", year_source="file", facts_count=len(x.shipments), created_by=user,
                         role="shipments_xlsx", status="ready", contains_personal_data=True)
    session.add(ds)
    session.flush()
    row.xlsx_dataset_id = ds.id
    row.xlsx_totals = {**_s(x.stated_totals), "adjustments": [{"label": a["label"], "tax": str(a["tax"]), "net": str(a["net"]), "base": str(a["base"]),
                                                               "other": str(a["other"]), "ref": a["source_ref"]} for a in x.adjustments]}
    for s in x.shipments:
        session.add(AramexShipment(invoice_id=row.id, source="xlsx", awb=s.awb, origin=s.origin, destination=s.destination, weight=s.weight,
                                   actual_weight=s.actual_weight, base=s.base, other=s.other, tax=s.tax, gross=s.gross, shipper_name=s.shipper_name,
                                   sent_by=s.sent_by, consignee_name=s.consignee_name, attention=s.attention))
    ds.summary = {"bill_doc": x.bill_doc, "issues": _issues(x.issues)}
    session.commit()
    return _result(session, row, ds)


def _ingest_reference(session, content, filename, user):
    """Scanned contract appendix: kept as a reference document. Nothing is read from it automatically."""
    digest, path = _store(content, filename)
    _duplicate(session, digest)
    try:
        import io

        import pdfplumber
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            pages = len(pdf.pages)
    except Exception as exc:
        raise AnalysisError(422, "The file is not a readable PDF") from exc
    ds = AnalysisDataset(module_id=MODULE_ID, layout="aramex_contract_reference", scope_label="reference_only", file_name=Path(filename).name, file_hash=digest,
                         storage_path=path, title="contract appendix (reference)", year_source="none", facts_count=0, created_by=user,
                         role="contract_reference", status="ready", summary={"pages": pages, "issues": []})
    session.add(ds)
    session.commit()
    return UploadResult("all", {"id": "all", "module": "aramex", "uploaded": {"dataset_id": ds.id, "role": ds.role, "file_name": ds.file_name, "status": ds.status,
                                                                  "note": "reference only: no figure is read from it"}}, 201)


def _result(session, row, ds) -> UploadResult:
    return UploadResult(f"inv:{row.id}", {**invoice_meta(session, row), "uploaded": {"dataset_id": ds.id, "role": ds.role, "file_name": ds.file_name, "status": ds.status}})


# ------------------------------------------------------------------------------------------------ queries
def invoices(session: Session) -> list[AramexInvoice]:
    return list(session.scalars(select(AramexInvoice).order_by(AramexInvoice.doc_date, AramexInvoice.id)).all())


def invoice_meta(session: Session, inv: AramexInvoice) -> dict:
    dss = [session.get(AnalysisDataset, i) for i in (inv.pdf_dataset_id, inv.xlsx_dataset_id) if i]
    n = {src: session.query(AramexShipment).filter_by(invoice_id=inv.id, source=src).count() for src in ("pdf", "xlsx")}
    complete = bool(inv.pdf_dataset_id and inv.xlsx_dataset_id)
    return {"id": f"inv:{inv.id}", "module": "aramex", "bill_doc": inv.bill_doc, "invoice_no": inv.invoice_no, "label": inv.invoice_no or inv.bill_doc,
            "doc_date": inv.doc_date.isoformat() if inv.doc_date else None, "has_pdf": bool(inv.pdf_dataset_id), "has_xlsx": bool(inv.xlsx_dataset_id),
            "shipments": {"pdf": n["pdf"], "xlsx": n["xlsx"]}, "status": "ready" if complete else "incomplete",
            "sources": [{"dataset_id": d.id, "role": d.role, "file_name": d.file_name, "status": d.status, "rows": d.facts_count} for d in dss],
            "issues": [i for d in dss for i in (d.summary or {}).get("issues", [])]}


def reference_documents(session: Session) -> list[AnalysisDataset]:
    return list(session.scalars(select(AnalysisDataset).where(AnalysisDataset.module_id == MODULE_ID, AnalysisDataset.role == "contract_reference")).all())


def _rows(session: Session, invoice_id: int, source: str) -> list[dict]:
    q = session.scalars(select(AramexShipment).where(AramexShipment.invoice_id == invoice_id, AramexShipment.source == source).order_by(AramexShipment.id))
    return [{c: getattr(r, c) for c in ("awb", "seq", "pickup_on", "route_text", "origin", "destination", "product", "pcs", "weight", "actual_weight", "base", "other",
                                        "net", "tax", "gross", "shipper_name", "sent_by", "consignee_name", "attention")} | {"invoice_id": invoice_id} for r in q]


def make_resolver(session: Session):
    """name -> party, confirmed against the official branch register (read-only); a name the register does not know keeps its own
    normalised text as key and is flagged unregistered. No fuzzy matching, no review items are created."""
    er = EntityResolver(session)
    info = {b.id: (b.name_ar or b.name_en or str(b.id), b.branch_type) for b in session.scalars(select(DimBranch)).all()}
    memo: dict[str, dict] = {}

    def resolve(name: str) -> dict:
        n = normalize_text(name)
        if n not in memo:
            bid = er.lookup("branch", name)
            if bid is not None and bid in info:
                disp, kind = info[bid]
                memo[n] = {"key": f"branch:{bid}", "display": disp, "kind": kind if kind in ("head_office", "unallocated") else "branch", "registered": True}
            else:
                memo[n] = {"key": f"name:{n}", "display": " ".join(name.split()), "kind": "branch", "registered": False}
        return memo[n]
    return resolve


def load_analysis_rows(session: Session, rules: allocation.Rules) -> tuple[list[dict], list[dict], dict]:
    """(allocated shipments of every complete invoice, merge exceptions, {invoice_id: info}). Invoices lacking a source are skipped here."""
    resolve = make_resolver(session)
    rows, exc, info = [], [], {}
    for inv in invoices(session):
        if not (inv.pdf_dataset_id and inv.xlsx_dataset_id):
            continue
        pdf, xl = _rows(session, inv.id, "pdf"), _rows(session, inv.id, "xlsx")
        for p in pdf:
            p["bill_doc"] = inv.bill_doc
        merged, e = engine.merge(pdf, xl)
        for r in merged:
            r["sender"] = allocation.allocate_side([r["shipper_name"], r["sent_by"]], r["origin"], rules, resolve)
            r["receiver"] = allocation.allocate_side([r["consignee_name"], r["attention"]], r["destination"], rules, resolve)
        rows += merged
        exc += [{**x, "invoice_id": inv.id, "bill_doc": inv.bill_doc} for x in e]
        info[inv.id] = {"id": inv.id, "bill_doc": inv.bill_doc, "invoice_no": inv.invoice_no, "doc_date": inv.doc_date, "due_date": inv.due_date,
                        "pdf_totals": {k: Decimal(v) for k, v in (inv.pdf_totals or {}).items()}, "n_pdf": len(pdf), "n_xlsx": len(xl),
                        "net_rows": sum((r["net"] for r in merged), Decimal(0))}
    return rows, exc, info


def reconcile_invoice(session: Session, invoice_id: int, tol: float) -> dict:
    inv = session.get(AramexInvoice, invoice_id)
    xt = {k: Decimal(v) for k, v in (inv.xlsx_totals or {}).items() if k != "adjustments"}
    adj = [{"label": a["label"], "tax": Decimal(a["tax"]), "net": Decimal(a["net"])} for a in (inv.xlsx_totals or {}).get("adjustments", [])]
    out = engine.reconcile(_rows(session, invoice_id, "pdf"), _rows(session, invoice_id, "xlsx"),
                           {k: Decimal(v) for k, v in (inv.pdf_totals or {}).items()}, xt, adj, tol)
    out["adjustments"] = adj
    return out


def delete_invoice(session: Session, invoice_id: int) -> None:
    inv = session.get(AramexInvoice, invoice_id)
    ids = [i for i in (inv.pdf_dataset_id, inv.xlsx_dataset_id) if i]
    session.execute(delete(AramexShipment).where(AramexShipment.invoice_id == invoice_id))
    session.delete(inv)
    session.flush()
    for i in ids:
        ds = session.get(AnalysisDataset, i)
        if ds:
            session.delete(ds)
    session.commit()


def delete_reference(session: Session, dataset_id: int) -> None:
    ds = session.get(AnalysisDataset, dataset_id)
    if ds is None or ds.role != "contract_reference":
        raise AnalysisError(404, "Reference document not found")
    session.delete(ds)
    session.commit()
