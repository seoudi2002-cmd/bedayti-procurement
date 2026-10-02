"""Pure value-cleaning helpers. No I/O, no DB: easy to test and reuse in every module."""
import re
import unicodedata
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation

_ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
_DIACRITICS = re.compile("[ً-ٰٟـ]")  # tashkeel + tatweel
_PUNCT = re.compile(r"[^\w\s]", re.UNICODE)
_SPACES = re.compile(r"\s+")
_CURRENCY_TOKENS = re.compile(r"(egp|usd|eur|sar|le|l\.e\.?|ج\.م\.?|جنيه|£|\$|€)", re.IGNORECASE)
_ARABIC_FOLD = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي", "ة": "ه", "ؤ": "و", "ئ": "ي"})


def normalize_text(value: object) -> str:
    """Canonical form for matching names/headers: case-, space-, punctuation- and Arabic-variant-insensitive."""
    if value is None:
        return ""
    text = unicodedata.normalize("NFKC", str(value)).translate(_ARABIC_DIGITS)
    text = _DIACRITICS.sub("", text).translate(_ARABIC_FOLD).casefold()
    text = _PUNCT.sub(" ", text.replace("_", " "))
    return _SPACES.sub(" ", text).strip()


def clean_text(value: object) -> str | None:
    """Display-safe text: trims and collapses whitespace but keeps the original spelling."""
    if value is None:
        return None
    text = _SPACES.sub(" ", unicodedata.normalize("NFKC", str(value))).strip()
    return text or None


def parse_number(value: object) -> Decimal | None:
    """Parse '1,234.50', '١٢٣٤٫٥', '(500)', '500-', '12 500 EGP', 7 -> Decimal. Raises ValueError if unparseable."""
    if value is None or isinstance(value, bool):
        if isinstance(value, bool):
            raise ValueError(f"not a number: {value!r}")
        return None
    if isinstance(value, (int, float, Decimal)):
        return Decimal(str(value))
    text = str(value).translate(_ARABIC_DIGITS).replace("٫", ".").replace("٬", ",").strip()
    if text == "" or text in {"-", "—", "n/a", "N/A", "NA"}:
        return None
    text = _CURRENCY_TOKENS.sub("", text).replace(" ", " ").strip()
    negative = False
    if text.startswith("(") and text.endswith(")"):
        negative, text = True, text[1:-1]
    if text.endswith("-"):
        negative, text = True, text[:-1]
    if text.startswith("-"):
        negative, text = True, text[1:]
    text = text.replace(" ", "")
    if "," in text and "." in text:
        # the right-most separator is the decimal mark
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        head, _, tail = text.rpartition(",")
        text = text.replace(",", "") if len(tail) == 3 and head else text.replace(",", ".")
    try:
        number = Decimal(text)
    except InvalidOperation:
        raise ValueError(f"not a number: {value!r}") from None
    return -number if negative else number


_DATE_FORMATS_DAYFIRST = ("%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y-%m-%d", "%Y/%m/%d", "%d/%m/%y", "%d-%b-%Y", "%d %b %Y")
_DATE_FORMATS_MONTHFIRST = ("%m/%d/%Y", "%m-%d-%Y", "%Y-%m-%d", "%Y/%m/%d", "%m/%d/%y", "%b %d, %Y")


def parse_date(value: object, dayfirst: bool = True) -> date | None:
    """Accepts date/datetime, Excel serial numbers, and common text formats. Raises ValueError if unparseable."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, (int, float, Decimal)) and not isinstance(value, bool):
        if 20000 < float(value) < 80000:  # plausible Excel serial (1954-2119)
            return (datetime(1899, 12, 30) + timedelta(days=float(value))).date()
        raise ValueError(f"not a date: {value!r}")
    text = str(value).translate(_ARABIC_DIGITS).strip()
    if not text:
        return None
    if re.match(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}", text):  # ISO datetime (how staged Excel dates are stored)
        return date.fromisoformat(text[:10])
    if re.fullmatch(r"\d{5}(\.\d+)?", text):
        return parse_date(float(text), dayfirst)
    formats = _DATE_FORMATS_DAYFIRST if dayfirst else _DATE_FORMATS_MONTHFIRST
    for fmt in formats:
        try:
            return datetime.strptime(text.split(" ")[0] if " " in text and ":" in text else text, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"not a date: {value!r}")


def month_start(d: date) -> date:
    return d.replace(day=1)


def parse_bool(value: object) -> bool | None:
    if value is None or str(value).strip() == "":
        return None
    text = normalize_text(value)
    if text in {"1", "true", "yes", "y", "نعم", "صح"}:
        return True
    if text in {"0", "false", "no", "n", "لا", "خطا"}:
        return False
    raise ValueError(f"not a boolean: {value!r}")


_EXCEL_ERRORS = {"#N/A", "#REF!", "#VALUE!", "#DIV/0!", "#NAME?", "#NUM!", "#NULL!"}


def excel_error(value: object) -> str | None:
    """Return the error literal when a cell holds an Excel formula error (kept as evidence, never as data)."""
    if isinstance(value, str) and value.strip().upper() in _EXCEL_ERRORS:
        return value.strip().upper()
    return None


def text_from_cell(value: object) -> str | None:
    """Text for identifiers/phones/codes that Excel may have stored as numbers (160130.0 -> '160130')."""
    if isinstance(value, bool):
        return clean_text(value)
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return clean_text(value)
