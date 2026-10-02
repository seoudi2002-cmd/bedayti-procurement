"""In-platform corrections. The original source value is NEVER overwritten: a correction is a separate record
with the original value, the corrected value, the reason, who proposed it, when, and its review status.
Only an approved correction changes the working value of the target record."""
from datetime import datetime

from sqlalchemy import DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin, TimestampMixin


class DataOverride(Base, IdMixin, TimestampMixin):  # created_at = proposed_at
    __tablename__ = "data_override"
    __table_args__ = (Index("ix_data_override_target", "entity_type", "entity_key", "field"),)

    entity_type: Mapped[str] = mapped_column(String(40))  # po_header | po_line | requisition | finance_handover | ...
    entity_key: Mapped[str] = mapped_column(String(120))  # natural key, e.g. "2026/36"
    field: Mapped[str] = mapped_column(String(60))
    value_type: Mapped[str] = mapped_column(String(10))  # text | number | integer | date
    original_value: Mapped[str | None] = mapped_column(Text)  # as it was in the source, kept forever
    corrected_value: Mapped[str | None] = mapped_column(Text)
    reason: Mapped[str] = mapped_column(Text)
    proposed_by: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(12), default="proposed")  # proposed|approved|rejected|superseded|reverted
    reviewed_by: Mapped[str | None] = mapped_column(String(200))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    review_note: Mapped[str | None] = mapped_column(Text)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
