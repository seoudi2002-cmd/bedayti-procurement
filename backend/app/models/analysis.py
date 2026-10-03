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
    # multi-file modules: the cycle (period) this file belongs to, its role there and its processing state
    cycle_id: Mapped[int | None] = mapped_column(ForeignKey("analysis_cycle.id"))
    role: Mapped[str | None] = mapped_column(String(24))  # statement | statement_word | invoice | evidence
    status: Mapped[str] = mapped_column(String(12), default="ready", server_default="ready")  # ready | processing | failed


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


class AnalysisCycle(Base, IdMixin, TimestampMixin):
    """One reporting period of a module whose sources arrive as several files (e.g. a copier consumption statement,
    its supplier invoice and supporting documents). Files of the same period are attached to one cycle."""

    __tablename__ = "analysis_cycle"
    __table_args__ = (UniqueConstraint("module_id", "period_year", "period_month", name="uq_analysis_cycle_period"),)

    module_id: Mapped[str] = mapped_column(String(64))
    period_year: Mapped[int] = mapped_column(Integer)
    period_month: Mapped[int] = mapped_column(Integer)
    label: Mapped[str | None] = mapped_column(String(200))


class CopierMachine(Base, IdMixin):
    """One machine row of the Part 1 consumption statement (primary operational source)."""

    __tablename__ = "copier_machine"
    __table_args__ = (Index("ix_copier_machine_dataset", "dataset_id"),)

    dataset_id: Mapped[int] = mapped_column(ForeignKey("analysis_dataset.id", ondelete="CASCADE"))
    source_ref: Mapped[str] = mapped_column(String(80))
    class_key: Mapped[str] = mapped_column(String(40))
    package: Mapped[int | None] = mapped_column(Integer)
    branch_source: Mapped[str] = mapped_column(String(300))  # as written
    branch_display: Mapped[str] = mapped_column(String(300))  # presentation only (stray marker removed)
    branch_key: Mapped[str] = mapped_column(String(300))
    branch_id: Mapped[int | None] = mapped_column(ForeignKey("dim_branch.id"))  # only when resolved via entity_alias
    seq: Mapped[int | None] = mapped_column(Integer)
    prev_reading: Mapped[int | None] = mapped_column(Integer)
    cur_reading: Mapped[int | None] = mapped_column(Integer)
    consumption: Mapped[int | None] = mapped_column(Integer)
    excess_stated: Mapped[int | None] = mapped_column(Integer)
    location_group: Mapped[str | None] = mapped_column(String(120))  # from Part 2 / Word (supporting)
    group_kind: Mapped[str | None] = mapped_column(String(20))
    rent_detail: Mapped[int | None] = mapped_column(Integer)  # rental value written in Part 2 (supporting)
    detail_sources: Mapped[list] = mapped_column(JsonType, default=list)
    flags: Mapped[list] = mapped_column(JsonType, default=list)


class CopierInvoice(Base, IdMixin):
    __tablename__ = "copier_invoice"

    dataset_id: Mapped[int] = mapped_column(ForeignKey("analysis_dataset.id", ondelete="CASCADE"), unique=True)
    internal_no: Mapped[str | None] = mapped_column(String(40))
    electronic_id: Mapped[str | None] = mapped_column(String(60))
    issued_on: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str | None] = mapped_column(String(40))
    seller_reg: Mapped[str | None] = mapped_column(String(40))
    buyer_reg: Mapped[str | None] = mapped_column(String(40))
    seller_name: Mapped[str | None] = mapped_column(String(300))
    buyer_name: Mapped[str | None] = mapped_column(String(300))
    totals: Mapped[dict] = mapped_column(JsonType, default=dict)  # as stated on the invoice
    issues: Mapped[list] = mapped_column(JsonType, default=list)


class CopierInvoiceLine(Base, IdMixin):
    __tablename__ = "copier_invoice_line"

    invoice_id: Mapped[int] = mapped_column(ForeignKey("copier_invoice.id", ondelete="CASCADE"))
    line_no: Mapped[int] = mapped_column(Integer)
    page: Mapped[int] = mapped_column(Integer)
    description: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(String(10))  # rent | excess | other
    packages: Mapped[list] = mapped_column(JsonType, default=list)
    color: Mapped[bool] = mapped_column(Boolean, default=False)
    a3: Mapped[bool] = mapped_column(Boolean, default=False)
    printers: Mapped[bool] = mapped_column(Boolean, default=False)
    qty: Mapped[Decimal | None] = mapped_column(Numeric(18, 5))
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 5))
    sales_total: Mapped[Decimal | None] = mapped_column(Numeric(18, 5))
    net_total: Mapped[Decimal | None] = mapped_column(Numeric(18, 5))
    vat_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 5))
    vat_rate: Mapped[Decimal | None] = mapped_column(Numeric(8, 3))
    wht_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 5))
    wht_rate: Mapped[Decimal | None] = mapped_column(Numeric(8, 3))
    total: Mapped[Decimal | None] = mapped_column(Numeric(18, 5))
    period_from: Mapped[date | None] = mapped_column(Date)
    period_to: Mapped[date | None] = mapped_column(Date)
    flags: Mapped[list] = mapped_column(JsonType, default=list)


class CopierEvidence(Base, IdMixin):
    """A scanned printer status page: SUPPORTING EVIDENCE ONLY. Never an input to KPIs, costs or totals."""

    __tablename__ = "copier_evidence"

    dataset_id: Mapped[int] = mapped_column(ForeignKey("analysis_dataset.id", ondelete="CASCADE"))
    page_no: Mapped[int] = mapped_column(Integer)
    counter_value: Mapped[int | None] = mapped_column(Integer)
    counter_raw: Mapped[str | None] = mapped_column(String(40))
    printed_at_text: Mapped[str | None] = mapped_column(String(40))
    confidence: Mapped[float | None] = mapped_column(Numeric(5, 2))
    status: Mapped[str] = mapped_column(String(16), default="unreadable")  # matched | no_match | unreadable | duplicate | ambiguous
    matched_machine_ref: Mapped[str | None] = mapped_column(String(80))
    note: Mapped[str | None] = mapped_column(String(300))


class CopierPaperRow(Base, IdMixin):
    """One distribution line of a paper-distribution statement (cartons of copier paper given to a branch / HQ department).
    Distribution = consumption, as the owner defines it. Priced from the purchase order's period price, not stored per row."""

    __tablename__ = "copier_paper_row"
    __table_args__ = (Index("ix_copier_paper_row_dataset", "dataset_id", "distributed_on"),)

    dataset_id: Mapped[int] = mapped_column(ForeignKey("analysis_dataset.id", ondelete="CASCADE"))
    source_ref: Mapped[str] = mapped_column(String(80))
    seq: Mapped[int | None] = mapped_column(Integer)
    cartons: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    branch_source: Mapped[str] = mapped_column(String(300))
    branch_display: Mapped[str] = mapped_column(String(300))
    branch_key: Mapped[str] = mapped_column(String(300))
    is_head_office: Mapped[bool] = mapped_column(Boolean, default=False)
    department: Mapped[str | None] = mapped_column(String(200))  # head-office department as written after "المركز الرئيسي"
    distributed_on: Mapped[date | None] = mapped_column(Date)
    flags: Mapped[list] = mapped_column(JsonType, default=list)
