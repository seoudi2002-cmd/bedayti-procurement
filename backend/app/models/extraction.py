"""Document extraction (scanned PDFs / native PDFs / Word) → reviewable proposals → confirmed facts.

Nothing extracted is a fact until a person confirms it. Every value keeps: the text exactly as read (`*_raw`),
the parsed value, a confidence (0-1), the page and the position it came from, and the flags raised while
validating it. The original file is stored once (document_file) and never changed.
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin, JsonType, TimestampMixin


class ExtractionJob(Base, IdMixin, TimestampMixin):
    __tablename__ = "extraction_job"

    file_id: Mapped[int] = mapped_column(ForeignKey("document_file.id"))
    status: Mapped[str] = mapped_column(String(12), default="queued")  # queued|running|done|failed
    engine: Mapped[str | None] = mapped_column(String(40))  # e.g. tesseract
    engine_version: Mapped[str | None] = mapped_column(String(80))
    languages: Mapped[str | None] = mapped_column(String(40))
    page_count: Mapped[int | None] = mapped_column(SmallInteger)
    params: Mapped[dict] = mapped_column(JsonType, default=dict)
    summary: Mapped[dict] = mapped_column(JsonType, default=dict)
    error: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[str | None] = mapped_column(String(200))


class ExtractedPage(Base, IdMixin):
    __tablename__ = "extracted_page"
    __table_args__ = (Index("ix_extracted_page_job", "job_id", "page_no", unique=True),)

    job_id: Mapped[int] = mapped_column(ForeignKey("extraction_job.id", ondelete="CASCADE"))
    page_no: Mapped[int] = mapped_column(SmallInteger)
    text_source: Mapped[str] = mapped_column(String(14))  # native_text | ocr | docx
    rotation: Mapped[int] = mapped_column(SmallInteger, default=0)
    mean_confidence: Mapped[float | None] = mapped_column(Numeric(5, 3))
    word_count: Mapped[int] = mapped_column(Integer, default=0)
    raw_text: Mapped[str] = mapped_column(Text, default="")  # exactly as read
    doc_type_guess: Mapped[str | None] = mapped_column(String(40))
    doc_type_confidence: Mapped[float | None] = mapped_column(Numeric(4, 3))
    image_path: Mapped[str | None] = mapped_column(String(1000))  # rendered page for the review screen


class ExtractedDocument(Base, IdMixin, TimestampMixin):
    """One logical document found inside a file (a PO, a requisition, a memo ...), spanning one or more pages."""

    __tablename__ = "extracted_document"

    job_id: Mapped[int] = mapped_column(ForeignKey("extraction_job.id", ondelete="CASCADE"))
    seq: Mapped[int] = mapped_column(SmallInteger)
    doc_type: Mapped[str] = mapped_column(String(40))
    page_from: Mapped[int] = mapped_column(SmallInteger)
    page_to: Mapped[int] = mapped_column(SmallInteger)
    status: Mapped[str] = mapped_column(String(14), default="pending_review")  # pending_review|confirmed|rejected
    confidence: Mapped[float | None] = mapped_column(Numeric(4, 3))
    # {field: {"value", "raw", "confidence", "page", "bbox"}} for PO number/date/supplier/requisition/total ...
    header: Mapped[dict] = mapped_column(JsonType, default=dict)
    flags: Mapped[list] = mapped_column(JsonType, default=list)
    po_header_id: Mapped[int | None] = mapped_column(ForeignKey("po_header.id"))
    link_method: Mapped[str | None] = mapped_column(String(40))  # po_number | requisition+supplier | manual
    procurement_document_id: Mapped[int | None] = mapped_column(ForeignKey("procurement_document.id"))
    reviewed_by: Mapped[str | None] = mapped_column(String(200))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    review_note: Mapped[str | None] = mapped_column(Text)


class ExtractedLine(Base, IdMixin, TimestampMixin):
    __tablename__ = "extracted_line"
    __table_args__ = (Index("ix_extracted_line_doc", "extracted_document_id", "line_no"),)

    extracted_document_id: Mapped[int] = mapped_column(ForeignKey("extracted_document.id", ondelete="CASCADE"))
    line_no: Mapped[int] = mapped_column(SmallInteger)
    page_no: Mapped[int | None] = mapped_column(SmallInteger)
    bbox: Mapped[dict | None] = mapped_column(JsonType)
    # as read (never edited)
    description_raw: Mapped[str | None] = mapped_column(Text)
    quantity_raw: Mapped[str | None] = mapped_column(String(60))
    unit_price_raw: Mapped[str | None] = mapped_column(String(60))
    line_total_raw: Mapped[str | None] = mapped_column(String(60))
    # parsed from the raw text; NULL when unreadable (never guessed)
    description: Mapped[str | None] = mapped_column(Text)
    unit_description: Mapped[str | None] = mapped_column(String(200))
    quantity: Mapped[float | None] = mapped_column(Numeric(18, 4))
    unit_price: Mapped[float | None] = mapped_column(Numeric(18, 5))
    line_total: Mapped[float | None] = mapped_column(Numeric(18, 5))
    price_basis: Mapped[str | None] = mapped_column(String(10))  # incl_vat | excl_vat | NULL (not stated)
    field_confidence: Mapped[dict] = mapped_column(JsonType, default=dict)
    confidence: Mapped[float | None] = mapped_column(Numeric(4, 3))
    flags: Mapped[list] = mapped_column(JsonType, default=list)
    status: Mapped[str] = mapped_column(String(12), default="extracted")  # extracted|reviewed|confirmed|rejected
    # branch evidence found in this line's own text only (never inferred)
    branch_source_text: Mapped[str | None] = mapped_column(String(600))
    branch_id: Mapped[int | None] = mapped_column(ForeignKey("dim_branch.id"))
    branch_attribution_method: Mapped[str | None] = mapped_column(String(40))
    branch_attribution_status: Mapped[str | None] = mapped_column(String(20))
    po_line_id: Mapped[int | None] = mapped_column(ForeignKey("fact_po_line.id"))  # set when confirmed


class PoLineAllocation(Base, IdMixin, TimestampMixin):
    """Which branch(es) a PO line (or part of it) was for. Rows come only from explicit evidence or a person's
    decision; the proposal/confirmation state and the source are always recorded."""

    __tablename__ = "po_line_allocation"
    __table_args__ = (Index("ix_po_line_allocation_line", "po_line_id"),)

    po_line_id: Mapped[int] = mapped_column(ForeignKey("fact_po_line.id", ondelete="CASCADE"))
    branch_id: Mapped[int] = mapped_column(ForeignKey("dim_branch.id"))
    quantity: Mapped[float | None] = mapped_column(Numeric(18, 4))
    amount: Mapped[float | None] = mapped_column(Numeric(18, 2))
    source: Mapped[str] = mapped_column(String(20))  # explicit_text | allocation_file | receipt_form | manual
    source_ref: Mapped[str | None] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(10), default="proposed")  # proposed | confirmed | rejected
    decided_by: Mapped[str | None] = mapped_column(String(200))
    note: Mapped[str | None] = mapped_column(Text)
