from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.documents import case_overview
from app.core.entities import resolve_alias
from app.core.modules.registry import get_registry
from app.db import get_session
from app.models import EntityAlias, FactPoLine, ImportBatch, PoHeader

router = APIRouter()
MODULE = "purchase_orders"


class AliasDecision(BaseModel):
    entity_id: int | None = None
    create_new: bool = False


@router.get("/aliases")
def list_aliases(status: str = "pending", entity_type: str | None = None, session: Session = Depends(get_session)):
    q = select(EntityAlias).where(EntityAlias.status == status).order_by(EntityAlias.entity_type, EntityAlias.alias_raw)
    if entity_type:
        q = q.where(EntityAlias.entity_type == entity_type)
    return [{"id": a.id, "entity_type": a.entity_type, "raw": a.alias_raw, "suggested_entity_id": a.entity_id,
             "confidence": float(a.confidence) if a.confidence is not None else None, "status": a.status}
            for a in session.scalars(q)]


@router.post("/aliases/{alias_id}/resolve")
def decide_alias(alias_id: int, body: AliasDecision, session: Session = Depends(get_session)):
    alias = session.get(EntityAlias, alias_id)
    if alias is None:
        raise HTTPException(404, "Alias not found")
    try:
        alias = resolve_alias(session, alias, body.entity_id, body.create_new)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {"id": alias.id, "status": alias.status, "entity_id": alias.entity_id}


@router.post("/imports/{batch_id}/rollback")
def rollback_import(batch_id: int, session: Session = Depends(get_session)):
    from app.modules.purchase_orders import loader
    batch = session.get(ImportBatch, batch_id)
    if batch is None or batch.module_id != MODULE:
        raise HTTPException(404, "Batch not found")
    loader.rollback(session, batch)
    return {"batch_id": batch.id, "status": batch.status}


@router.get("/purchase-orders")
def list_pos(fiscal_year: int | None = None, supplier_id: int | None = None, limit: int = 100,
             session: Session = Depends(get_session)):
    q = select(PoHeader).order_by(PoHeader.po_date.desc(), PoHeader.id.desc()).limit(min(limit, 500))
    if fiscal_year:
        q = q.where(PoHeader.fiscal_year == fiscal_year)
    if supplier_id:
        q = q.where(PoHeader.supplier_id == supplier_id)
    return [{"id": h.id, "fiscal_year": h.fiscal_year, "po_number": h.po_number, "po_date": h.po_date,
             "supplier_id": h.supplier_id, "total_amount": float(h.total_amount), "status": h.status}
            for h in session.scalars(q)]


@router.get("/purchase-orders/{po_id}")
def get_po(po_id: int, session: Session = Depends(get_session)):
    h = session.get(PoHeader, po_id)
    if h is None:
        raise HTTPException(404, "PO not found")
    lines = session.scalars(select(FactPoLine).where(FactPoLine.po_header_id == po_id).order_by(FactPoLine.line_number))
    overview = case_overview(session, get_registry().get(MODULE), h.case_id) if h.case_id else None
    return {
        "id": h.id, "fiscal_year": h.fiscal_year, "po_number": h.po_number, "po_date": h.po_date,
        "approval_date": h.approval_date, "supplier_id": h.supplier_id, "requisition_no": h.requisition_no,
        "purchase_method": h.purchase_method, "payment_days": h.payment_days, "delivery_days": h.delivery_days,
        "total_amount": float(h.total_amount), "currency": h.currency, "status": h.status,
        "lines": [{"line_number": ln.line_number, "item": ln.item_description, "quantity": float(ln.quantity),
                   "unit_price": float(ln.unit_price), "line_amount": float(ln.line_amount),
                   "branch_id": ln.branch_id, "category_id": ln.category_id} for ln in lines],
        "documents": [{"type": d.doc_type, "number": d.doc_number, "date": d.doc_date, "amount": d.amount and float(d.amount)}
                      for d in overview["documents"]] if overview else [],
        "current_stage": overview["current_stage"] if overview else None,
        "missing_required_documents": overview["missing_required"] if overview else [],
    }
