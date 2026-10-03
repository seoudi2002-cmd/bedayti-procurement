"""Analysis datasets (uploaded report files) and their parsed facts, plus editable system settings.

Analysis modules do not manage transactions: a dataset is one uploaded file, its facts are the numbers the file
states (one row per non-zero cell/line, with the source cell reference). Nothing is invented: a dimension the file
does not carry (period year, branch, category ...) is NULL and the report says the file does not support it."""
from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin, JsonType, TimestampMixin


class AppSetting(Base, TimestampMixin):
    """System settings editable without code changes (e.g. outlier thresholds, approved display taxonomy)."""

    __tablename__ = "app_setting"

    key: Mapped[str] = mapped_column(String(120), primary_key=True)
    value: Mapped[dict] = mapped_column(JsonType)
    updated_by: Mapped[str | None] = mapped_column(String(200))


class AnalysisDataset(Base, IdMixin, TimestampMixin):
    __tablename__ = "analysis_dataset"
    __table_args__ = (UniqueConstraint("module_id", "file_hash", name="uq_analysis_dataset_file"),)

    module_id: Mapped[str] = mapped_column(String(64))
    layout: Mapped[str] = mapped_column(String(40))  # gl_settlement_lines | monthly_branch_expense | monthly_custodian_expense ...
    scope_label: Mapped[str] = mapped_column(String(40))  # temporary_custody | head_office | branches ...
    file_name: Mapped[str] = mapped_column(String(500))
    file_hash: Mapped[str] = mapped_column(String(64))
    storage_path: Mapped[str | None] = mapped_column(String(1000))
    title: Mapped[str | None] = mapped_column(String(300))
    period_year: Mapped[int | None] = mapped_column(Integer)  # as stated in the file or supplied by the uploader
    year_source: Mapped[str | None] = mapped_column(String(40))  # file | uploader | other_sheets | none
    period_from: Mapped[date | None] = mapped_column(Date)
    period_to: Mapped[date | None] = mapped_column(Date)
    facts_count: Mapped[int] = mapped_column(Integer, default=0)
    summary: Mapped[dict] = mapped_column(JsonType, default=dict)  # presence rows, control totals, issues, labels
    created_by: Mapped[str | None] = mapped_column(String(200))
    contains_personal_data: Mapped[bool] = mapped_column(Boolean, default=False)


class AnalysisFact(Base, IdMixin):
    __tablename__ = "analysis_fact"
    __table_args__ = (Index("ix_analysis_fact_dataset", "dataset_id", "period_month"),)

    dataset_id: Mapped[int] = mapped_column(ForeignKey("analysis_dataset.id", ondelete="CASCADE"))
    source_ref: Mapped[str] = mapped_column(String(80))  # sheet!cell or sheet!row — lineage to the file
    period_year: Mapped[int | None] = mapped_column(Integer)
    period_month: Mapped[int | None] = mapped_column(Integer)
    scope: Mapped[str] = mapped_column(String(20))  # head_office | branch | unspecified
    branch_key: Mapped[str | None] = mapped_column(String(200))
    branch_label: Mapped[str | None] = mapped_column(String(300))  # as written in the file
    branch_kind: Mapped[str | None] = mapped_column(String(12))  # branch | group | head_office
    branch_id: Mapped[int | None] = mapped_column(ForeignKey("dim_branch.id"))  # only when resolved via entity_alias
    cost_center_code: Mapped[str | None] = mapped_column(String(40))
    category_source: Mapped[str | None] = mapped_column(String(200))  # original expense class name
    item_source: Mapped[str | None] = mapped_column(String(200))  # original sub-item name, when the file has one
    account_no: Mapped[str | None] = mapped_column(String(40))
    holder_text: Mapped[str | None] = mapped_column(String(300))  # personal data: admin only
    ref_no: Mapped[str | None] = mapped_column(String(80))  # e.g. journal-entry number
    description_raw: Mapped[str | None] = mapped_column(Text)  # personal data: admin only
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    flags: Mapped[list] = mapped_column(JsonType, default=list)
