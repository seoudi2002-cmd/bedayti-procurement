"""Fact tables (Layer C).

fact_cost / fact_usage are the conformed tables every module writes to, which is what makes
cross-module questions ("total admin cost per branch") a single query. Module-specific detail
(fact_po_line, fact_savings) sits beside them where depth is needed.
"""
from datetime import date

from sqlalchemy import Date, ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin, JsonType, TimestampMixin


class LineageMixin:
    batch_id: Mapped[int | None] = mapped_column(ForeignKey("import_batch.id", ondelete="CASCADE"))
    raw_row_id: Mapped[int | None] = mapped_column(ForeignKey("raw_row.id", ondelete="SET NULL"))


class FactCost(Base, IdMixin, TimestampMixin, LineageMixin):
    __tablename__ = "fact_cost"
    __table_args__ = (
        Index("ix_fact_cost_module_period", "module_id", "period"),
        Index("ix_fact_cost_branch_period", "branch_id", "period"),
        Index("ix_fact_cost_supplier_period", "supplier_id", "period"),
    )

    module_id: Mapped[str] = mapped_column(ForeignKey("report_module.id"))
    period: Mapped[date] = mapped_column(ForeignKey("dim_period.period"))
    branch_id: Mapped[int | None] = mapped_column(ForeignKey("dim_branch.id"))
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("dim_supplier.id"))
    category_id: Mapped[int | None] = mapped_column(ForeignKey("dim_category.id"))
    cost_center_id: Mapped[int | None] = mapped_column(ForeignKey("dim_cost_center.id"))
    asset_id: Mapped[int | None] = mapped_column(ForeignKey("dim_asset.id"))
    amount: Mapped[float] = mapped_column(Numeric(18, 2))
    currency: Mapped[str] = mapped_column(String(3), default="EGP")
    attrs: Mapped[dict] = mapped_column(JsonType, default=dict)


class FactUsage(Base, IdMixin, TimestampMixin, LineageMixin):
    """Non-monetary quantities: pages, reams, km, litres, shipments, kg ..."""

    __tablename__ = "fact_usage"
    __table_args__ = (
        Index("ix_fact_usage_module_metric_period", "module_id", "metric_code", "period"),
        Index("ix_fact_usage_branch_period", "branch_id", "period"),
    )

    module_id: Mapped[str] = mapped_column(ForeignKey("report_module.id"))
    period: Mapped[date] = mapped_column(ForeignKey("dim_period.period"))
    branch_id: Mapped[int | None] = mapped_column(ForeignKey("dim_branch.id"))
    asset_id: Mapped[int | None] = mapped_column(ForeignKey("dim_asset.id"))
    metric_code: Mapped[str] = mapped_column(String(64))
    quantity: Mapped[float] = mapped_column(Numeric(18, 4))
    unit: Mapped[str] = mapped_column(String(20))
    attrs: Mapped[dict] = mapped_column(JsonType, default=dict)


class FactPoLine(Base, IdMixin, TimestampMixin, LineageMixin):
    """Purchase-order line: the detail behind procurement spend and price-variance analysis."""

    __tablename__ = "fact_po_line"
    __table_args__ = (
        Index("ix_fact_po_line_po", "po_number", "line_number"),
        Index("ix_fact_po_line_item_date", "item_id", "po_date"),
    )

    po_number: Mapped[str] = mapped_column(String(64))
    line_number: Mapped[int] = mapped_column(Integer, default=1)
    po_date: Mapped[date] = mapped_column(Date)
    period: Mapped[date] = mapped_column(ForeignKey("dim_period.period"))
    branch_id: Mapped[int | None] = mapped_column(ForeignKey("dim_branch.id"))
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("dim_supplier.id"))
    category_id: Mapped[int | None] = mapped_column(ForeignKey("dim_category.id"))
    item_id: Mapped[int | None] = mapped_column(ForeignKey("dim_item.id"))
    item_description: Mapped[str | None] = mapped_column(String(500))
    quantity: Mapped[float] = mapped_column(Numeric(18, 4))
    uom: Mapped[str | None] = mapped_column(String(20))
    unit_price: Mapped[float] = mapped_column(Numeric(18, 4))
    line_amount: Mapped[float] = mapped_column(Numeric(18, 2))
    currency: Mapped[str] = mapped_column(String(3), default="EGP")
    requested_by: Mapped[str | None] = mapped_column(String(200))
    required_date: Mapped[date | None] = mapped_column(Date)
    received_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str | None] = mapped_column(String(30))
    attrs: Mapped[dict] = mapped_column(JsonType, default=dict)


class FactSavings(Base, IdMixin, TimestampMixin, LineageMixin):
    __tablename__ = "fact_savings"
    __table_args__ = (Index("ix_fact_savings_period", "period"),)

    period: Mapped[date] = mapped_column(ForeignKey("dim_period.period"))
    po_line_id: Mapped[int | None] = mapped_column(ForeignKey("fact_po_line.id"))
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("dim_supplier.id"))
    category_id: Mapped[int | None] = mapped_column(ForeignKey("dim_category.id"))
    item_id: Mapped[int | None] = mapped_column(ForeignKey("dim_item.id"))
    # negotiation | consolidation | specification | demand_reduction | cost_avoidance ...
    savings_type: Mapped[str] = mapped_column(String(30))
    baseline_amount: Mapped[float] = mapped_column(Numeric(18, 2))
    actual_amount: Mapped[float] = mapped_column(Numeric(18, 2))
    savings_amount: Mapped[float] = mapped_column(Numeric(18, 2))
    status: Mapped[str] = mapped_column(String(20), default="identified")  # identified|realized
    attrs: Mapped[dict] = mapped_column(JsonType, default=dict)


class FactBudget(Base, IdMixin, TimestampMixin, LineageMixin):
    __tablename__ = "fact_budget"
    __table_args__ = (Index("ix_fact_budget_period_branch", "period", "branch_id"),)

    module_id: Mapped[str | None] = mapped_column(ForeignKey("report_module.id"))
    period: Mapped[date] = mapped_column(ForeignKey("dim_period.period"))
    branch_id: Mapped[int | None] = mapped_column(ForeignKey("dim_branch.id"))
    category_id: Mapped[int | None] = mapped_column(ForeignKey("dim_category.id"))
    amount: Mapped[float] = mapped_column(Numeric(18, 2))
    currency: Mapped[str] = mapped_column(String(3), default="EGP")
