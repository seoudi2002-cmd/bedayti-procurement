"""PO header and the procurement document graph.

A *case* is one end-to-end transaction (requisition → quotes → committee approval → PO → receipt →
inspection → invoice → payment). Every paper/electronic document in that chain is a `procurement_document`
tied to the case (and to the PO header once it exists). Only the PO is loaded in Phase 1b; the rest
attach later through core/documents.py without schema changes.
"""
from datetime import date

from sqlalchemy import Date, ForeignKey, Index, Integer, Numeric, SmallInteger, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin, JsonType, TimestampMixin


class DocumentFile(Base, IdMixin, TimestampMixin):
    """A stored scan/PDF/e-invoice file. Content extraction (OCR/AI) is a later, human-verified step."""

    __tablename__ = "document_file"

    file_name: Mapped[str] = mapped_column(String(500))
    source_kind: Mapped[str | None] = mapped_column(String(14))  # pdf_scanned | pdf_native | docx | xlsx ...
    sha256: Mapped[str] = mapped_column(String(64), unique=True)
    storage_path: Mapped[str | None] = mapped_column(String(1000))
    content_type: Mapped[str | None] = mapped_column(String(100))
    pages: Mapped[int | None] = mapped_column(SmallInteger)
    uploaded_by: Mapped[str | None] = mapped_column(String(200))


class ProcurementCase(Base, IdMixin, TimestampMixin):
    __tablename__ = "procurement_case"

    case_key: Mapped[str] = mapped_column(String(100), unique=True)  # e.g. 2026-PO-35, stable once set
    fiscal_year: Mapped[int] = mapped_column(SmallInteger)
    title: Mapped[str | None] = mapped_column(String(500))
    cost_center_id: Mapped[int | None] = mapped_column(ForeignKey("dim_cost_center.id"))
    opened_on: Mapped[date | None] = mapped_column(Date)
    attrs: Mapped[dict] = mapped_column(JsonType, default=dict)


class PoHeader(Base, IdMixin, TimestampMixin):
    __tablename__ = "po_header"
    __table_args__ = (
        # PO numbers restart each fiscal year (PO No. 35 of 2026 vs No. 35 of 2025)
        UniqueConstraint("fiscal_year", "po_number", name="uq_po_header_fy_number"),
        Index("ix_po_header_supplier_period", "supplier_id", "period"),
        Index("ix_po_header_requisition", "fiscal_year", "requisition_no"),
    )

    fiscal_year: Mapped[int] = mapped_column(SmallInteger)
    po_number: Mapped[str] = mapped_column(String(64))
    number_source: Mapped[str | None] = mapped_column(String(64))  # as written in the source, e.g. "35/2026"
    # NULL = missing or invalid in the source (kept as po_date_source); never replaced by a guess
    po_date: Mapped[date | None] = mapped_column(Date)
    po_date_source: Mapped[str | None] = mapped_column(String(50))
    approval_date: Mapped[date | None] = mapped_column(Date)  # last signature, can lag po_date
    period: Mapped[date | None] = mapped_column(ForeignKey("dim_period.period"))
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("dim_supplier.id"))
    supplier_name_source: Mapped[str | None] = mapped_column(String(300))
    supplier_register_no_source: Mapped[int | None] = mapped_column(Integer)
    cost_center_id: Mapped[int | None] = mapped_column(ForeignKey("dim_cost_center.id"))  # requesting unit
    # Branch attribution is auditable: who/what assigned it, from which text, and whether a person must review.
    branch_id: Mapped[int | None] = mapped_column(ForeignKey("dim_branch.id"))
    branch_source_text: Mapped[str | None] = mapped_column(String(600))
    branch_attribution_method: Mapped[str | None] = mapped_column(String(40))
    branch_attribution_status: Mapped[str | None] = mapped_column(String(20))  # auto_assigned|needs_review|confirmed
    requisition_no: Mapped[str | None] = mapped_column(String(64))
    requisition_id: Mapped[int | None] = mapped_column(ForeignKey("requisition.id"))
    purchase_method: Mapped[str | None] = mapped_column(String(50))  # e.g. negotiated / tender / direct
    delivery_days: Mapped[int | None] = mapped_column(Integer)
    payment_days: Mapped[int | None] = mapped_column(Integer)  # days after receipt
    payment_terms: Mapped[str | None] = mapped_column(String(300))
    currency: Mapped[str] = mapped_column(String(3), default="EGP")
    # 'lines' = total derives from fact_po_line; 'header_only' = total as stated in the PO register
    granularity: Mapped[str] = mapped_column(String(12), default="lines", server_default="lines")
    total_amount: Mapped[float | None] = mapped_column(Numeric(18, 2))  # NULL = not stated (never 0)
    lines_total: Mapped[float | None] = mapped_column(Numeric(18, 2))  # sum of confirmed lines; compared with total_amount
    description_source: Mapped[str | None] = mapped_column(Text)
    po_category_source: Mapped[str | None] = mapped_column(String(200))
    supplier_category_source: Mapped[str | None] = mapped_column(String(200))
    issuance_status_source: Mapped[str | None] = mapped_column(String(100))
    order_status_source: Mapped[str | None] = mapped_column(String(100))
    # Register columns "amount paid"/"remaining" are NOT confirmed bank payments: they are the amounts
    # recorded as handed to Finance until a payment ledger with bank dates exists.
    finance_handover_amount_register: Mapped[float | None] = mapped_column(Numeric(18, 2))
    remaining_register: Mapped[float | None] = mapped_column(Numeric(18, 2))
    status: Mapped[str | None] = mapped_column(String(30))
    case_id: Mapped[int | None] = mapped_column(ForeignKey("procurement_case.id"))
    batch_id: Mapped[int | None] = mapped_column(ForeignKey("import_batch.id", ondelete="SET NULL"))
    # contract clauses not worth a column yet: late_penalty_pct_per_week, penalty_cap_pct,
    # quantity_tolerance_pct, warranty_months ...
    terms: Mapped[dict] = mapped_column(JsonType, default=dict)
    attrs: Mapped[dict] = mapped_column(JsonType, default=dict)


class ProcurementDocument(Base, IdMixin, TimestampMixin):
    __tablename__ = "procurement_document"
    __table_args__ = (
        Index("ix_procurement_document_type_number", "doc_type", "doc_number"),
        Index("ix_procurement_document_case", "case_id"),
        Index("ix_procurement_document_po", "po_header_id"),
    )

    case_id: Mapped[int | None] = mapped_column(ForeignKey("procurement_case.id"))
    po_header_id: Mapped[int | None] = mapped_column(ForeignKey("po_header.id"))
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("procurement_document.id"))
    relation: Mapped[str | None] = mapped_column(String(30))  # e.g. "invoices", "fulfils", "approves"
    doc_type: Mapped[str] = mapped_column(String(40))  # must be a code in the module's document_types
    doc_number: Mapped[str | None] = mapped_column(String(100))
    doc_date: Mapped[date | None] = mapped_column(Date)
    fiscal_year: Mapped[int | None] = mapped_column(SmallInteger)
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("dim_supplier.id"))
    amount: Mapped[float | None] = mapped_column(Numeric(18, 2))
    currency: Mapped[str] = mapped_column(String(3), default="EGP")
    status: Mapped[str | None] = mapped_column(String(30))
    file_id: Mapped[int | None] = mapped_column(ForeignKey("document_file.id"))
    batch_id: Mapped[int | None] = mapped_column(ForeignKey("import_batch.id", ondelete="SET NULL"))
    # typed register row this envelope stands for (e.g. requisition / finance_handover), if any
    page_from: Mapped[int | None] = mapped_column(SmallInteger)  # pages of file_id this document occupies
    page_to: Mapped[int | None] = mapped_column(SmallInteger)
    ref_table: Mapped[str | None] = mapped_column(String(40))
    ref_id: Mapped[int | None] = mapped_column()
    # type-specific details, e.g. invoice: {tax_registration, e_invoice_uuid, po_reference};
    # inspection: {result, inspector}; payment: {due_date, bank_reference}
    attrs: Mapped[dict] = mapped_column(JsonType, default=dict)
