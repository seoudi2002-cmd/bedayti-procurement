"""Business-level data exceptions (cross-record issues needing a person's review).

Row-level parse problems stay in validation_issue; this table holds things like "duplicate PO number",
"manager differs between branch file and HR", "possible duplicate finance memo". Source records are never
modified to make an exception go away: an exception is closed by a decision (accepted/resolved/dismissed)
or by a corrected re-import.
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin, JsonType, TimestampMixin


class DataException(Base, IdMixin, TimestampMixin):
    __tablename__ = "data_exception"
    __table_args__ = (
        UniqueConstraint("code", "entity_type", "entity_key", name="uq_data_exception_key"),
        Index("ix_data_exception_status", "status", "severity"),
    )

    module_id: Mapped[str | None] = mapped_column(String(64))
    code: Mapped[str] = mapped_column(String(64))
    severity: Mapped[str] = mapped_column(String(10))  # info | warning | error
    status: Mapped[str] = mapped_column(String(12), default="open")  # open|accepted|resolved|dismissed
    entity_type: Mapped[str] = mapped_column(String(30))  # po_header, supplier, employee, import_batch ...
    entity_key: Mapped[str] = mapped_column(String(100))  # natural key, e.g. "2026/36"
    batch_id: Mapped[int | None] = mapped_column(ForeignKey("import_batch.id", ondelete="SET NULL"))
    message: Mapped[str] = mapped_column(Text)
    details: Mapped[dict] = mapped_column(JsonType, default=dict)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decided_by: Mapped[str | None] = mapped_column(String(200))
    decision_note: Mapped[str | None] = mapped_column(Text)
