"""Source registers that are not purchase orders: requisitions and finance handover memos.

Source text (status, categories, subjects) is stored verbatim in *_source columns. Nothing here is a
confirmed payment: finance_handover is what was handed to Finance, not what the bank paid.
"""
from datetime import date

from sqlalchemy import Date, ForeignKey, Index, Integer, Numeric, SmallInteger, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin, JsonType, TimestampMixin
from app.models.facts import LineageMixin


class Requisition(Base, IdMixin, TimestampMixin, LineageMixin):
    __tablename__ = "requisition"
    __table_args__ = (UniqueConstraint("fiscal_year", "req_number", name="uq_requisition_fy_number"),)

    fiscal_year: Mapped[int] = mapped_column(SmallInteger)
    req_number: Mapped[str] = mapped_column(String(64))
    number_source: Mapped[str] = mapped_column(String(64))  # e.g. "35/2026"
    source_seq: Mapped[int | None] = mapped_column(Integer)
    request_date: Mapped[date | None] = mapped_column(Date)  # NULL = missing/invalid in source (see exceptions)
    department_id: Mapped[int | None] = mapped_column(ForeignKey("dim_department.id"))
    department_source: Mapped[str | None] = mapped_column(String(200))
    description_source: Mapped[str | None] = mapped_column(Text)
    priority_source: Mapped[str | None] = mapped_column(String(50))
    status_source: Mapped[str | None] = mapped_column(String(100))
    notes_source: Mapped[str | None] = mapped_column(Text)
    case_id: Mapped[int | None] = mapped_column(ForeignKey("procurement_case.id"))
    attrs: Mapped[dict] = mapped_column(JsonType, default=dict)


class FinanceHandover(Base, IdMixin, TimestampMixin, LineageMixin):
    """A memo handing an amount to Finance. memo_type 'po' (against a PO) or 'service' (no PO: recurring
    administrative/service payments). Kept in one register but never folded into the PO register."""

    __tablename__ = "finance_handover"
    __table_args__ = (
        UniqueConstraint("memo_no", name="uq_finance_handover_memo_no"),
        Index("ix_finance_handover_po", "po_header_id"),
        Index("ix_finance_handover_type_date", "memo_type", "sent_date"),
    )

    memo_no: Mapped[int] = mapped_column(Integer)  # running number in the source sheet
    memo_type: Mapped[str] = mapped_column(String(10))  # po | service
    memo_type_source: Mapped[str] = mapped_column(String(50))
    sent_date: Mapped[date | None] = mapped_column(Date)
    po_number_source: Mapped[str | None] = mapped_column(String(64))
    po_header_id: Mapped[int | None] = mapped_column(ForeignKey("po_header.id"))
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("dim_supplier.id"))
    supplier_name_source: Mapped[str | None] = mapped_column(String(300))
    supplier_category_source: Mapped[str | None] = mapped_column(String(200))
    subject_source: Mapped[str | None] = mapped_column(Text)
    purchase_category_source: Mapped[str | None] = mapped_column(String(200))
    amount: Mapped[float | None] = mapped_column(Numeric(18, 2))
    currency: Mapped[str] = mapped_column(String(3), default="EGP")
    period: Mapped[date | None] = mapped_column(ForeignKey("dim_period.period"))
    attrs: Mapped[dict] = mapped_column(JsonType, default=dict)
