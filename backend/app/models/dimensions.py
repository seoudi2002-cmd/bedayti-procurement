"""Conformed dimensions (Layer B) shared by every module so reports are comparable."""
from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, Index, Integer, Numeric, SmallInteger, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin, JsonType, TimestampMixin


class DimPeriod(Base):
    """One row per calendar month; period = first day of the month."""

    __tablename__ = "dim_period"

    period: Mapped[date] = mapped_column(Date, primary_key=True)
    year: Mapped[int] = mapped_column(SmallInteger)
    quarter: Mapped[int] = mapped_column(SmallInteger)
    month: Mapped[int] = mapped_column(SmallInteger)
    fiscal_year: Mapped[int] = mapped_column(SmallInteger)


class DimBranch(Base, IdMixin, TimestampMixin):
    __tablename__ = "dim_branch"

    code: Mapped[str] = mapped_column(String(32), unique=True)
    name_en: Mapped[str | None] = mapped_column(String(200))
    name_ar: Mapped[str | None] = mapped_column(String(200))
    region: Mapped[str | None] = mapped_column(String(100))
    branch_type: Mapped[str | None] = mapped_column(String(50))
    # Normalisation drivers for fair branch comparison (per m², per head ...)
    area_m2: Mapped[float | None] = mapped_column(Numeric(12, 2))
    headcount: Mapped[int | None] = mapped_column(Integer)
    opened_on: Mapped[date | None] = mapped_column(Date)
    closed_on: Mapped[date | None] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    attrs: Mapped[dict] = mapped_column(JsonType, default=dict)


class DimSupplier(Base, IdMixin, TimestampMixin):
    __tablename__ = "dim_supplier"

    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(300))
    name_ar: Mapped[str | None] = mapped_column(String(300))
    tax_id: Mapped[str | None] = mapped_column(String(50))
    primary_category_id: Mapped[int | None] = mapped_column(ForeignKey("dim_category.id"))
    status: Mapped[str] = mapped_column(String(20), default="active")
    attrs: Mapped[dict] = mapped_column(JsonType, default=dict)


class DimCategory(Base, IdMixin, TimestampMixin):
    """Hierarchical spend taxonomy (e.g. Admin > Printing > Toner)."""

    __tablename__ = "dim_category"
    __table_args__ = (UniqueConstraint("parent_id", "name"),)

    parent_id: Mapped[int | None] = mapped_column(ForeignKey("dim_category.id"))
    code: Mapped[str | None] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    level: Mapped[int] = mapped_column(SmallInteger, default=1)


class DimItem(Base, IdMixin, TimestampMixin):
    __tablename__ = "dim_item"

    sku: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(300))
    category_id: Mapped[int | None] = mapped_column(ForeignKey("dim_category.id"))
    uom: Mapped[str | None] = mapped_column(String(20))
    attrs: Mapped[dict] = mapped_column(JsonType, default=dict)


class DimAsset(Base, IdMixin, TimestampMixin):
    """Machines, vehicles, leased premises ... anything costs are attached to."""

    __tablename__ = "dim_asset"
    __table_args__ = (UniqueConstraint("asset_type", "code"),)

    asset_type: Mapped[str] = mapped_column(String(32))  # copier | vehicle | lease | ...
    code: Mapped[str] = mapped_column(String(64))
    name: Mapped[str | None] = mapped_column(String(200))
    branch_id: Mapped[int | None] = mapped_column(ForeignKey("dim_branch.id"))
    attrs: Mapped[dict] = mapped_column(JsonType, default=dict)


class DimCostCenter(Base, IdMixin, TimestampMixin):
    __tablename__ = "dim_cost_center"

    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(200))


class EntityAlias(Base, IdMixin, TimestampMixin):
    """Maps messy source text ("Maadi Br.", "المعادي") to a canonical dimension row."""

    __tablename__ = "entity_alias"
    __table_args__ = (
        UniqueConstraint("entity_type", "alias_norm", name="uq_entity_alias_type_norm"),
        Index("ix_entity_alias_entity", "entity_type", "entity_id"),
    )

    entity_type: Mapped[str] = mapped_column(String(20))  # branch | supplier | category | item
    alias_raw: Mapped[str] = mapped_column(String(400))
    alias_norm: Mapped[str] = mapped_column(String(400))  # output of normalize_text()
    # approved: the canonical row. pending: the *suggested* row (fuzzy match) or null if none was close.
    entity_id: Mapped[int | None] = mapped_column()
    confidence: Mapped[float | None] = mapped_column(Numeric(4, 3))
    status: Mapped[str] = mapped_column(String(12), default="pending")  # pending|approved|rejected
