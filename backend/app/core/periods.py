"""Calendar/fiscal helpers shared by pipeline and loaders."""
from datetime import date

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.dimensions import DimPeriod


def fiscal_year(d: date, start_month: int | None = None) -> int:
    """Fiscal years are named by the calendar year in which they END.

    start_month=1 (default) -> FY == calendar year. start_month=7 -> Jul-2025..Jun-2026 is FY2026.
    """
    start = start_month or get_settings().fiscal_year_start_month
    return d.year if start == 1 or d.month < start else d.year + 1


def ensure_period(session: Session, d: date) -> date:
    first = d.replace(day=1)
    if session.get(DimPeriod, first) is None:
        session.add(DimPeriod(period=first, year=first.year, quarter=(first.month - 1) // 3 + 1,
                              month=first.month, fiscal_year=fiscal_year(first)))
        session.flush()
    return first
