"""Evaluate declarative KPI specs against fact tables.

Supports `aggregate` (sum/avg/count/count_distinct/min/max over a fact column) and `ratio`
(one KPI divided by another over the same slice). Anything fancier (concentration, price
variance) belongs in the insight engine, not here.
"""
from datetime import date
from decimal import Decimal

from sqlalchemy import Select, distinct, func, select
from sqlalchemy.orm import Session

from app.core.modules.spec import KpiSpec, ReportModuleSpec
from app import models

FACT_TABLES = {
    "fact_cost": models.FactCost,
    "fact_usage": models.FactUsage,
    "fact_po_line": models.FactPoLine,
    "fact_savings": models.FactSavings,
    "fact_budget": models.FactBudget,
    "po_header": models.PoHeader,
    "finance_handover": models.FinanceHandover,
}
GROUP_COLUMNS = {
    "period": "period", "branch": "branch_id", "supplier": "supplier_id",
    "category": "category_id", "item": "item_id", "asset": "asset_id",
}


def _aggregate(spec: KpiSpec, group_by: str | None, date_from: date | None, date_to: date | None,
               module_id: str) -> Select:
    model = FACT_TABLES.get(spec.source or "")
    if model is None:
        raise ValueError(f"KPI '{spec.code}': unknown source table '{spec.source}'")
    col = getattr(model, spec.column) if spec.column else None
    fn = {
        "sum": lambda: func.sum(col), "avg": lambda: func.avg(col), "min": lambda: func.min(col),
        "max": lambda: func.max(col), "count": lambda: func.count(),
        "count_distinct": lambda: func.count(distinct(col)),
    }[spec.agg]()
    cols = [fn.label("value")]
    group_col = None
    if group_by:
        attr = GROUP_COLUMNS.get(group_by)
        if attr is None or not hasattr(model, attr):
            raise ValueError(f"KPI '{spec.code}' cannot be grouped by '{group_by}' (table {spec.source})")
        group_col = getattr(model, attr)
        cols.insert(0, group_col.label("key"))
    q = select(*cols).select_from(model)  # count(*) has no column to infer the FROM from
    if hasattr(model, "module_id") and spec.source in ("fact_cost", "fact_usage"):
        q = q.where(model.module_id == module_id)
    if date_from:
        q = q.where(model.period >= date_from)
    if date_to:
        q = q.where(model.period <= date_to)
    for k, v in spec.where.items():
        q = q.where(getattr(model, k) == v)
    for k in spec.where_not_null:
        q = q.where(getattr(model, k).is_not(None))
    return q.group_by(group_col) if group_col is not None else q


def compute_kpi(
    session: Session, module: ReportModuleSpec, code: str, date_from: date | None = None,
    date_to: date | None = None, group_by: str | None = None,
) -> dict:
    """Return {slice_key: value}; the key is None when not grouped. Missing/zero denominators give None."""
    spec = module.kpi(code)
    if spec.kind == "ratio":
        num = compute_kpi(session, module, spec.numerator, date_from, date_to, group_by)
        den = compute_kpi(session, module, spec.denominator, date_from, date_to, group_by)
        out = {}
        for key, n in num.items():
            d = den.get(key)
            out[key] = None if n is None or not d else float(Decimal(str(n)) / Decimal(str(d)) * Decimal(str(spec.scale)))
        return out
    rows = session.execute(_aggregate(spec, group_by, date_from, date_to, module.manifest.id)).all()
    if not group_by:
        v = rows[0].value if rows else None
        return {None: None if v is None else float(v)}
    return {r.key: None if r.value is None else float(r.value) for r in rows}
