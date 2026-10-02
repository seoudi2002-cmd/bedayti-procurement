"""Analytics outputs (Layer D). KPI *definitions* live in module YAML; only results are stored."""
from datetime import date, datetime

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin, JsonType, TimestampMixin


class KpiValue(Base, IdMixin, TimestampMixin):
    __tablename__ = "kpi_value"
    __table_args__ = (
        Index("ix_kpi_value_lookup", "module_id", "kpi_code", "period"),
        Index("uq_kpi_value_key", "module_id", "kpi_code", "period", "dimension", "dimension_id", unique=True),
    )

    module_id: Mapped[str] = mapped_column(ForeignKey("report_module.id"))
    kpi_code: Mapped[str] = mapped_column(String(64))
    period: Mapped[date] = mapped_column(ForeignKey("dim_period.period"))
    # Slice the value applies to: "total" (id 0), "branch", "supplier", "category" ...
    dimension: Mapped[str] = mapped_column(String(20), default="total")
    dimension_id: Mapped[int] = mapped_column(default=0)
    value: Mapped[float | None] = mapped_column(Numeric(20, 6))
    prior_period_value: Mapped[float | None] = mapped_column(Numeric(20, 6))
    prior_year_value: Mapped[float | None] = mapped_column(Numeric(20, 6))
    budget_value: Mapped[float | None] = mapped_column(Numeric(20, 6))


class Insight(Base, IdMixin, TimestampMixin):
    """Rule-generated finding (spike, outlier, price variance ...). The AI explains these; it does not invent them."""

    __tablename__ = "insight"
    __table_args__ = (Index("ix_insight_module_period", "module_id", "period"),)

    module_id: Mapped[str] = mapped_column(ForeignKey("report_module.id"))
    rule_code: Mapped[str] = mapped_column(String(64))
    severity: Mapped[str] = mapped_column(String(10))  # info | warning | critical
    period: Mapped[date | None] = mapped_column(ForeignKey("dim_period.period"))
    dimension: Mapped[str | None] = mapped_column(String(20))
    dimension_id: Mapped[int | None] = mapped_column()
    title: Mapped[str] = mapped_column(String(300))
    detail: Mapped[str | None] = mapped_column(Text)
    estimated_impact: Mapped[float | None] = mapped_column(Numeric(18, 2))
    evidence: Mapped[dict] = mapped_column(JsonType, default=dict)  # KPI codes, row ids, thresholds
    status: Mapped[str] = mapped_column(String(12), default="open")  # open|accepted|dismissed|done


class SavedReport(Base, IdMixin, TimestampMixin):
    __tablename__ = "saved_report"

    name: Mapped[str] = mapped_column(String(200))
    template_code: Mapped[str] = mapped_column(String(64))
    params: Mapped[dict] = mapped_column(JsonType, default=dict)  # modules, branches, period range
    created_by: Mapped[str | None] = mapped_column(String(200))


class ReportRun(Base, IdMixin, TimestampMixin):
    __tablename__ = "report_run"

    saved_report_id: Mapped[int | None] = mapped_column(ForeignKey("saved_report.id"))
    output_format: Mapped[str] = mapped_column(String(10))  # xlsx | pdf | pptx
    status: Mapped[str] = mapped_column(String(12), default="queued")
    storage_path: Mapped[str | None] = mapped_column(String(1000))
    ai_summary: Mapped[str | None] = mapped_column(Text)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
