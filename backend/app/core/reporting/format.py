"""Shared number/month formatting and table-column helper for module report builders."""
from decimal import Decimal

MONTH_NAMES = {
    "ar": ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو", "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"],
    "en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
}


def money(v) -> str:
    return f"{Decimal(v):,.0f}"


def money2(v) -> str:
    return f"{Decimal(v):,.2f}"


def pct(v) -> str:
    return "—" if v is None else f"{v:.1f}%"


def spct(v) -> str:
    return "—" if v is None else f"{v:+.1f}%"


def smoney(v) -> str:
    return f"{Decimal(v):+,.0f}"


def col(key, label, fmt="text"):
    return {"key": key, "label": label, "fmt": fmt}


def period_label(lang: str, period, short: bool = False) -> str:
    y, m = period
    name = MONTH_NAMES[lang][m - 1]
    return f"{name} {str(y)[2:] if short else y}" if y else name
