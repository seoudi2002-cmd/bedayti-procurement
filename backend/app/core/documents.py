"""Attach workflow documents (requisition, quotes, invoice, payment ...) to a procurement case / PO.

Phase 1b loads only POs, but every PO already gets a case and an anchoring `purchase_order` document, so the
rest of the chain can be linked later (manual entry, file upload, or AI-assisted extraction with human
verification) without schema changes.
"""
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.modules.spec import ReportModuleSpec
from app.models import PoHeader, ProcurementCase, ProcurementDocument, Requisition


class DocumentLinkError(ValueError):
    pass


def _case_key(header: PoHeader) -> str:
    return f"{header.fiscal_year}-PO-{header.po_number}"


def requisition_case_key(fiscal_year: int, req_number: str) -> str:
    return f"{fiscal_year}-REQ-{req_number}"


def ensure_requisition_case(session: Session, req: Requisition) -> ProcurementCase:
    key = requisition_case_key(req.fiscal_year, req.req_number)
    case = session.scalar(select(ProcurementCase).where(ProcurementCase.case_key == key))
    if case is None:
        case = ProcurementCase(case_key=key, fiscal_year=req.fiscal_year, opened_on=req.request_date)
        session.add(case)
        session.flush()
    req.case_id = case.id
    doc = session.scalar(select(ProcurementDocument).where(
        ProcurementDocument.ref_table == "requisition", ProcurementDocument.ref_id == req.id))
    if doc is None:
        session.add(ProcurementDocument(
            case_id=case.id, doc_type="requisition", doc_number=req.number_source, doc_date=req.request_date,
            fiscal_year=req.fiscal_year, status=req.status_source, ref_table="requisition", ref_id=req.id,
            batch_id=req.batch_id))
    else:
        doc.case_id, doc.doc_date, doc.status = case.id, req.request_date, req.status_source
    session.flush()
    return case


def link_po_to_requisition(session: Session, header: PoHeader, req: Requisition) -> None:
    """Attach a PO to its requisition's case, moving documents out of a PO-only case created earlier."""
    header.requisition_id = req.id
    target = req.case_id or ensure_requisition_case(session, req).id
    if header.case_id and header.case_id != target:
        old = header.case_id
        for doc in session.scalars(select(ProcurementDocument).where(ProcurementDocument.case_id == old)):
            doc.case_id = target
        header.case_id = target
        session.flush()
        if not session.scalar(select(ProcurementDocument.id).where(ProcurementDocument.case_id == old).limit(1)):
            leftover = session.get(ProcurementCase, old)
            if leftover is not None:
                session.delete(leftover)
    header.case_id = target
    session.flush()


def ensure_po_anchor(session: Session, header: PoHeader) -> ProcurementCase:
    """Idempotently give a PO header its case and its purchase_order document."""
    case = session.get(ProcurementCase, header.case_id) if header.case_id else None
    if case is None:
        case = session.scalar(select(ProcurementCase).where(ProcurementCase.case_key == _case_key(header)))
    if case is None:
        case = ProcurementCase(case_key=_case_key(header), fiscal_year=header.fiscal_year,
                               cost_center_id=header.cost_center_id, opened_on=header.po_date)
        session.add(case)
        session.flush()
    header.case_id = case.id
    doc = session.scalar(select(ProcurementDocument).where(
        ProcurementDocument.po_header_id == header.id, ProcurementDocument.doc_type == "purchase_order"))
    if doc is None:
        session.add(ProcurementDocument(
            case_id=case.id, po_header_id=header.id, doc_type="purchase_order", doc_number=header.po_number,
            doc_date=header.po_date, fiscal_year=header.fiscal_year, supplier_id=header.supplier_id,
            amount=header.total_amount, currency=header.currency, status=header.status,
            batch_id=header.batch_id))
    else:
        doc.amount, doc.doc_date, doc.supplier_id = header.total_amount, header.po_date, header.supplier_id
    session.flush()
    return case


def find_po(session: Session, fiscal_year: int, po_number: str | None = None,
            requisition_no: str | None = None) -> PoHeader | None:
    q = select(PoHeader).where(PoHeader.fiscal_year == fiscal_year)
    if po_number is not None:
        q = q.where(PoHeader.po_number == po_number)
    elif requisition_no is not None:
        q = q.where(PoHeader.requisition_no == requisition_no)
    else:
        return None
    return session.scalars(q).first()


def attach_document(
    session: Session, spec: ReportModuleSpec, doc_type: str, *, fiscal_year: int,
    po_number: str | None = None, requisition_no: str | None = None, doc_number: str | None = None,
    doc_date: date | None = None, supplier_id: int | None = None, amount: float | None = None,
    currency: str = "EGP", status: str | None = None, file_id: int | None = None,
    parent_id: int | None = None, relation: str | None = None, attrs: dict | None = None,
) -> ProcurementDocument:
    """Link a document to the case of an existing PO (found by PO number or requisition number)."""
    if doc_type not in {d.code for d in spec.manifest.document_types}:
        raise DocumentLinkError(f"Unknown document type '{doc_type}' for module {spec.manifest.id}")
    header = find_po(session, fiscal_year, po_number, requisition_no)
    if header is None:
        raise DocumentLinkError(
            f"No PO found for fiscal year {fiscal_year} (po_number={po_number}, requisition_no={requisition_no})")
    case = ensure_po_anchor(session, header)
    doc = ProcurementDocument(
        case_id=case.id, po_header_id=header.id, parent_id=parent_id, relation=relation, doc_type=doc_type,
        doc_number=doc_number, doc_date=doc_date, fiscal_year=fiscal_year, supplier_id=supplier_id or header.supplier_id,
        amount=amount, currency=currency, status=status, file_id=file_id, attrs=attrs or {})
    session.add(doc)
    session.commit()
    return doc


def case_overview(session: Session, spec: ReportModuleSpec, case_id: int) -> dict:
    """Documents on file in lifecycle order, current stage, and which required documents are still missing."""
    types = {d.code: d for d in spec.manifest.document_types}
    docs = session.scalars(select(ProcurementDocument).where(ProcurementDocument.case_id == case_id)).all()
    docs.sort(key=lambda d: (types[d.doc_type].stage if d.doc_type in types else 99, d.doc_date or date.min))
    present = {d.doc_type for d in docs}
    stage = max((types[t].stage for t in present if t in types), default=0)
    return {
        "documents": docs,
        "current_stage": next((t.code for t in types.values() if t.stage == stage), None),
        "missing_required": [t.code for t in sorted(types.values(), key=lambda t: t.stage)
                             if t.required and t.code not in present],
    }
