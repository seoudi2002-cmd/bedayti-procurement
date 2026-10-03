"""Aramex domestic e-invoice (PDF): header, one line per shipment (with the pick-up date), and the invoice's own totals.

Lines are read from the PDF text; every line that looks like a shipment but cannot be read is reported, never skipped silently.
The Arabic 'Operational details' lines are not used (the Excel carries the parties)."""
import io
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal

import pdfplumber

_ITEM = re.compile(r"^(\d+)\s+(\d{8,14})\s+(\d\d/\d\d/\d{4})\s+(.+?)\s+([A-Z]{2,4})\s+([\d.]+)\s*KG\s+(\d+)\s+([\d,]+\.\d\d)\s+([\d,]+\.\d\d)\s+([\d,]+\.\d\d)\s*$")
_ITEM_START = re.compile(r"^\d+\s+\d{8,14}\s+\d\d/\d\d/\d{4}\b")
_NUM = r"([\d,]+\.\d\d)"


class UnrecognisedInvoice(ValueError):
    pass


@dataclass
class PdfShipment:
    seq: int
    awb: str
    pickup_on: date
    route_text: str
    product: str
    weight: Decimal
    pcs: int
    base: Decimal
    other: Decimal
    net: Decimal


@dataclass
class Issue:
    code: str
    severity: str
    message: str
    count: int = 1
    examples: list[str] = field(default_factory=list)


@dataclass
class AramexPdf:
    invoice_no: str | None = None
    bill_doc: str | None = None
    doc_date: date | None = None
    due_date: date | None = None
    customer_no: str | None = None
    currency: str | None = None
    totals: dict[str, Decimal] = field(default_factory=dict)   # net, vat, total, vat_rate_pct
    shipments: list[PdfShipment] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)
    pages: int = 0

    def issue(self, code, severity, message, example=None):
        for i in self.issues:
            if i.code == code:
                i.count += 1
                if example and len(i.examples) < 10:
                    i.examples.append(example)
                return
        self.issues.append(Issue(code, severity, message, 1, [example] if example else []))


def _d(s: str) -> date:
    return datetime.strptime(s, "%m/%d/%Y").date()


def _n(s: str) -> Decimal:
    return Decimal(s.replace(",", ""))


def has_text(content: bytes) -> bool:
    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            return any((p.extract_text() or "").strip() for p in pdf.pages[:3])
    except Exception:
        return False


def parse_invoice(content: bytes) -> AramexPdf:
    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            pages = [(p.extract_text() or "") for p in pdf.pages]
    except Exception as exc:
        raise UnrecognisedInvoice(f"Not a readable PDF: {exc}") from exc
    text = "\n".join(pages)
    if "Domestic Outbound Summary Invoice" not in text and "HAWB" not in text:
        raise UnrecognisedInvoice("Not an Aramex domestic summary invoice")
    inv = AramexPdf(pages=len(pages))
    if m := re.search(r"Invoice Number:\s*(\S+)", text):
        inv.invoice_no = m.group(1)
        if mb := re.search(r"/(\d+)", m.group(1)):
            inv.bill_doc = mb.group(1)
    if m := re.search(r"Document Date:\s*(\d\d/\d\d/\d{4})", text):
        inv.doc_date = _d(m.group(1))
    if m := re.search(r"Due Date:\s*(\d\d/\d\d/\d{4})", text):
        inv.due_date = _d(m.group(1))
    if m := re.search(r"^(\d{6,})\s+.+?\s+([A-Z]{3})\s*$", text, re.M):
        inv.customer_no, inv.currency = m.group(1), m.group(2)
    for line in text.splitlines():
        line = line.strip()
        m = _ITEM.match(line)
        if m:
            seq, awb, d, route, prod, kg, pcs, base, other, net = m.groups()
            inv.shipments.append(PdfShipment(int(seq), awb, _d(d), route, prod, Decimal(kg), int(pcs), _n(base), _n(other), _n(net)))
        elif _ITEM_START.match(line):
            inv.issue("unreadable_line", "critical", "A shipment line could not be read (its amounts are not counted)", line[:90])
    if not inv.shipments:
        raise UnrecognisedInvoice("No shipment lines found")
    if m := re.search(r"Total Net Amount:\s*" + _NUM, text):
        inv.totals["net"] = _n(m.group(1))
    if m := re.search(r"VAT\s*([\d.]+)\s*%\s*" + _NUM, text):
        inv.totals["vat_rate_pct"], inv.totals["vat"] = Decimal(m.group(1)), _n(m.group(2))
    if m := re.search(r"Total Invoice Amount:\s*(?:[A-Z]{3}\s*)?" + _NUM, text):
        inv.totals["total"] = _n(m.group(1))
    _validate(inv)
    return inv


def _validate(inv: AramexPdf) -> None:
    if not inv.bill_doc:
        inv.issue("no_invoice_number", "critical", "The invoice number could not be read; the Excel cannot be linked")
    seqs = [s.seq for s in inv.shipments]
    missing = [i for i in range(1, max(seqs) + 1) if i not in set(seqs)]
    if missing:
        inv.issue("sequence_gaps", "critical", "Missing line numbers in the invoice", "missing: " + ", ".join(map(str, missing[:12])))
    seen: dict[str, int] = {}
    for s in inv.shipments:
        seen[s.awb] = seen.get(s.awb, 0) + 1
    for awb, c in seen.items():
        if c > 1:
            inv.issue("duplicate_awb", "critical", "The same AWB appears on more than one invoice line", awb)
    for s in inv.shipments:
        if s.base + s.other != s.net:
            inv.issue("line_arithmetic", "warning", "Base + other charges differ from the line's net amount", f"line {s.seq}: {s.base}+{s.other}≠{s.net}")
    tot = sum((s.net for s in inv.shipments), Decimal(0))
    if "net" in inv.totals and inv.totals["net"] != tot:
        inv.issue("net_total_differs", "critical", "Σ line net differs from the invoice's Total Net Amount", f"lines {tot} vs stated {inv.totals['net']}")
    if "net" in inv.totals and "vat" in inv.totals and "total" in inv.totals and inv.totals["net"] + inv.totals["vat"] != inv.totals["total"]:
        inv.issue("total_arithmetic", "critical", "Net + VAT differs from the stated invoice total")
