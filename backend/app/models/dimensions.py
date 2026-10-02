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


class DimRegion(Base, IdMixin, TimestampMixin):
    __tablename__ = "dim_region"

    name: Mapped[str] = mapped_column(String(200), unique=True)  # as written in the branch master


class DimDepartment(Base, IdMixin, TimestampMixin):
    """Requesting departments. No department master exists yet: rows come from source values (see `source`)."""

    __tablename__ = "dim_department"

    name: Mapped[str] = mapped_column(String(200), unique=True)
    source: Mapped[str | None] = mapped_column(String(100))


class DimBranch(Base, IdMixin, TimestampMixin):
    """Branch master. `code` is only ever filled from an official source: never generated.

    branch_type: branch | head_office | regional_office | unallocated. The two system rows
    (Head Office, Unallocated / Branch Not Identified) are identified by `system_key`.
    """

    __tablename__ = "dim_branch"

    code: Mapped[str | None] = mapped_column(String(32), unique=True)
    system_key: Mapped[str | None] = mapped_column(String(32), unique=True)
    source_seq: Mapped[int | None] = mapped_column(Integer)  # running number in the branch master file
    region_id: Mapped[int | None] = mapped_column(ForeignKey("dim_region.id"))
    address: Mapped[str | None] = mapped_column(String(600))
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


class BranchContact(Base, IdMixin, TimestampMixin):
    """PERSONAL DATA (admin-only): managers' names, phones, e-mail. Kept apart from dim_branch so reports
    and dashboards that join dim_branch never expose it. Source values are never overwritten."""

    __tablename__ = "branch_contact"

    branch_id: Mapped[int] = mapped_column(ForeignKey("dim_branch.id"), unique=True)
    branch_manager_name_source: Mapped[str | None] = mapped_column(String(300))
    branch_phone: Mapped[str | None] = mapped_column(String(100))
    manager_phone_1: Mapped[str | None] = mapped_column(String(100))
    manager_phone_2: Mapped[str | None] = mapped_column(String(100))
    region_manager_name_source: Mapped[str | None] = mapped_column(String(300))
    region_manager_phone: Mapped[str | None] = mapped_column(String(200))
    email: Mapped[str | None] = mapped_column(String(200))
    notes_source: Mapped[str | None] = mapped_column(String(500))
    # reconciliation with the HR file: both values are kept, disagreement is a status, not an overwrite
    manager_employee_id: Mapped[int | None] = mapped_column(ForeignKey("dim_employee.id"))
    manager_reconciliation_status: Mapped[str | None] = mapped_column(String(30))


class DimEmployee(Base, IdMixin, TimestampMixin):
    """PERSONAL DATA (admin-only). Master from the HR 'actives' file.

    Fields the source does not contain (department, cost centre, manager) stay NULL *and* are listed in
    `missing_fields`, so "not provided" is never confused with "none"/zero.
    """

    __tablename__ = "dim_employee"

    employee_code: Mapped[int] = mapped_column(unique=True)
    full_name: Mapped[str] = mapped_column(String(300))
    hire_date: Mapped[date | None] = mapped_column(Date)
    position_source: Mapped[str | None] = mapped_column(String(200))
    branch_id: Mapped[int | None] = mapped_column(ForeignKey("dim_branch.id"))
    branch_source_text: Mapped[str | None] = mapped_column(String(300))
    branch_match_method: Mapped[str | None] = mapped_column(String(30))  # exact|compact|alias|unresolved
    governorate_source: Mapped[str | None] = mapped_column(String(100))
    governorate_issue: Mapped[str | None] = mapped_column(String(50))  # e.g. source_error:#N/A
    department_id: Mapped[int | None] = mapped_column(ForeignKey("dim_department.id"))
    cost_center_id: Mapped[int | None] = mapped_column(ForeignKey("dim_cost_center.id"))
    manager_employee_id: Mapped[int | None] = mapped_column(ForeignKey("dim_employee.id"))
    missing_fields: Mapped[list] = mapped_column(JsonType, default=list)
    source_batch_id: Mapped[int | None] = mapped_column(ForeignKey("import_batch.id", ondelete="SET NULL"))


class DimSupplier(Base, IdMixin, TimestampMixin):
    """Supplier register. Source category/services text is kept verbatim (no taxonomy mapping yet);
    contact people/phones/e-mail live in supplier_contact (admin-only)."""

    __tablename__ = "dim_supplier"

    code: Mapped[str | None] = mapped_column(String(32), unique=True)  # SUPnnn from the register
    register_no: Mapped[int | None] = mapped_column(Integer)  # NOT unique in the source (see data_exception)
    name: Mapped[str] = mapped_column(String(300))
    name_ar: Mapped[str | None] = mapped_column(String(300))
    commercial_reg_no: Mapped[str | None] = mapped_column(String(60))
    address: Mapped[str | None] = mapped_column(String(600))
    category_source: Mapped[str | None] = mapped_column(String(200))
    services_source: Mapped[str | None] = mapped_column(String(300))
    notes_source: Mapped[str | None] = mapped_column(String(500))
    tax_id: Mapped[str | None] = mapped_column(String(50))  # raw text as in the source, never reformatted
    primary_category_id: Mapped[int | None] = mapped_column(ForeignKey("dim_category.id"))
    status: Mapped[str] = mapped_column(String(20), default="active")
    attrs: Mapped[dict] = mapped_column(JsonType, default=dict)


class SupplierContact(Base, IdMixin, TimestampMixin):
    """PERSONAL DATA (admin-only)."""

    __tablename__ = "supplier_contact"

    supplier_id: Mapped[int] = mapped_column(ForeignKey("dim_supplier.id"), unique=True)
    contact_name_source: Mapped[str | None] = mapped_column(String(300))
    phone_source: Mapped[str | None] = mapped_column(String(100))
    email: Mapped[str | None] = mapped_column(String(200))


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

    code: Mapped[str | None] = mapped_column(String(32), unique=True)
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
    status: Mapped[str] = mapped_column(String(12), default="pending")  # pending|approved
    method: Mapped[str | None] = mapped_column(String(30))  # who/what approved it: review | system_seed
