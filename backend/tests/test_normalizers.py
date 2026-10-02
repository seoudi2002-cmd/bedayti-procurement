from datetime import date, datetime
from decimal import Decimal

import pytest

from app.core.cleaning.normalizers import normalize_text, parse_bool, parse_date, parse_number


@pytest.mark.parametrize("raw,expected", [
    ("1,234.50", "1234.50"), ("١٢٣٤٫٥", "1234.5"), ("(500)", "-500"), ("500-", "-500"),
    ("12 500 EGP", "12500"), ("1.234,50", "1234.50"), ("1,234", "1234"), ("12,5", "12.5"),
    (7, "7"), (3.5, "3.5"), ("  ", None), (None, None), ("-", None),
])
def test_parse_number(raw, expected):
    got = parse_number(raw)
    assert (got is None and expected is None) or got == Decimal(expected)


def test_parse_number_rejects_garbage():
    with pytest.raises(ValueError):
        parse_number("abc")


def test_parse_date_variants():
    assert parse_date("05/01/2025") == date(2025, 1, 5)
    assert parse_date("05/01/2025", dayfirst=False) == date(2025, 5, 1)
    assert parse_date(datetime(2025, 3, 2, 10)) == date(2025, 3, 2)
    assert parse_date(45658) == date(2025, 1, 1)  # Excel serial
    assert parse_date("٠٥/٠١/٢٠٢٥") == date(2025, 1, 5)
    with pytest.raises(ValueError):
        parse_date("soon")


def test_normalize_text_arabic_and_punctuation():
    assert normalize_text("  المَعَادِي ") == normalize_text("المعادي")
    assert normalize_text("أحمد") == normalize_text("احمد")
    assert normalize_text("Maadi  Br.") == "maadi br"
    assert normalize_text("PO_No") == "po no"


def test_parse_bool():
    assert parse_bool("Yes") is True and parse_bool("لا") is False and parse_bool("") is None
