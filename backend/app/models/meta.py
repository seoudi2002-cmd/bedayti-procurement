"""Import pipeline + module registry metadata (Layer A)."""
from datetime import date, datetime

from sqlalchemy import (
    Boolean, Date, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IdMixin, JsonType, TimestampMixin


class ReportModule(Base, TimestampMixin):
    """Mirror of a module package on disk; the YAML files stay the source of truth."""

    __tablename__ = "report_module"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # e.g. "purchase_orders"
    name: Mapped[str] = mapped_column(String(200))
    version: Mapped[str] = mapped_column(String(32))
    category: Mapped[str] = mapped_column(String(64))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    config: Mapped[dict] = mapped_column(JsonType, default=dict)


class MappingTemplate(Base, IdMixin, TimestampMixin):
    """Saved column mapping for a recurring source-file layout."""

    __tablename__ = "mapping_template"
    __table_args__ = (UniqueConstraint("module_id", "name"),)

    module_id: Mapped[str] = mapped_column(ForeignKey("report_module.id"))
    name: Mapped[str] = mapped_column(String(200))
    header_signature: Mapped[str] = mapped_column(String(64))  # hash of normalized headers
    column_map: Mapped[dict] = mapped_column(JsonType)  # {source_header: canonical_field}
    options: Mapped[dict] = mapped_column(JsonType, default=dict)  # sheet, header_row, date format


class ImportBatch(Base, IdMixin, TimestampMixin):
    __tablename__ = "import_batch"
    __table_args__ = (
        # one live batch per file; a rolled-back file may be uploaded again
        Index("uq_import_batch_module_file", "module_id", "file_hash", unique=True,
              postgresql_where=text("status <> 'rolled_back'"), sqlite_where=text("status <> 'rolled_back'")),
        Index("ix_import_batch_module_period", "module_id", "period_from"),
    )

    module_id: Mapped[str] = mapped_column(ForeignKey("report_module.id"))
    file_name: Mapped[str] = mapped_column(String(500))
    file_hash: Mapped[str] = mapped_column(String(64))  # sha256, blocks duplicate uploads
    storage_path: Mapped[str | None] = mapped_column(String(1000))
    sheet_name: Mapped[str | None] = mapped_column(String(200))
    profile: Mapped[str] = mapped_column(String(30), default="default", server_default="default")
    column_map: Mapped[dict | None] = mapped_column(JsonType)  # {source header: field} used at validation
    warnings: Mapped[list] = mapped_column(JsonType, default=list, server_default="[]")  # e.g. data-freshness warnings
    mapping_template_id: Mapped[int | None] = mapped_column(ForeignKey("mapping_template.id"))
    period_from: Mapped[date | None] = mapped_column(Date)
    period_to: Mapped[date | None] = mapped_column(Date)
    # uploaded -> staged -> validated -> loaded | partially_loaded | rolled_back
    status: Mapped[str] = mapped_column(String(20), default="uploaded")
    rows_total: Mapped[int] = mapped_column(Integer, default=0)
    rows_valid: Mapped[int] = mapped_column(Integer, default=0)
    rows_rejected: Mapped[int] = mapped_column(Integer, default=0)
    rows_skipped: Mapped[int] = mapped_column(Integer, default=0, server_default="0")  # subtotals, blanks ...
    rows_loaded: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    rows_held: Mapped[int] = mapped_column(Integer, default=0, server_default="0")  # waiting on entity review
    created_by: Mapped[str | None] = mapped_column(String(200))
    loaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    rows: Mapped[list["RawRow"]] = relationship(back_populates="batch", cascade="all, delete-orphan")


class RawRow(Base, IdMixin):
    """Immutable source row (payload) plus its cleaned form. Facts point back here for lineage."""

    __tablename__ = "raw_row"
    __table_args__ = (Index("ix_raw_row_batch_row", "batch_id", "row_number"),)

    batch_id: Mapped[int] = mapped_column(ForeignKey("import_batch.id", ondelete="CASCADE"))
    sheet_name: Mapped[str | None] = mapped_column(String(200))
    row_number: Mapped[int] = mapped_column(Integer)
    payload: Mapped[dict] = mapped_column(JsonType)  # original cells keyed by source header
    cleaned: Mapped[dict | None] = mapped_column(JsonType)  # canonical fields after cleaning
    status: Mapped[str] = mapped_column(String(12), default="pending")  # pending|valid|rejected|held|loaded|skipped

    batch: Mapped[ImportBatch] = relationship(back_populates="rows")


class ValidationIssue(Base, IdMixin, TimestampMixin):
    __tablename__ = "validation_issue"
    __table_args__ = (Index("ix_validation_issue_batch", "batch_id", "severity"),)

    batch_id: Mapped[int] = mapped_column(ForeignKey("import_batch.id", ondelete="CASCADE"))
    raw_row_id: Mapped[int | None] = mapped_column(ForeignKey("raw_row.id", ondelete="CASCADE"))
    severity: Mapped[str] = mapped_column(String(10))  # error | warning
    code: Mapped[str] = mapped_column(String(64))  # e.g. missing_required, bad_number
    field: Mapped[str | None] = mapped_column(String(100))
    message: Mapped[str] = mapped_column(Text)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
