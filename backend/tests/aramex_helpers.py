"""Synthetic Aramex files that mimic the structure of the real ones (no real data)."""
import functools
import io
from datetime import date, datetime
from decimal import Decimal

from openpyxl import Workbook

# (awb, pickup, origin, destination, weight, actual, pcs, base, shipper_name, sent_by, consignee_name, attention, product)
HQ_CONTACT = "Hq Person"
SHIPMENTS_A = [   # invoice A: 29-31 Aug 2026 (a Saturday .. Monday)
    ("1000000001", date(2026, 8, 29), "Giza", "Fayoum", Decimal("0.5"), Decimal("0.5"), 1, 60, "Company HQ", HQ_CONTACT, "شركة بدايتي فرع الفيوم", "x", "OND"),       # HQ -> branch
    ("1000000002", date(2026, 8, 29), "Fayoum", "Agouza", Decimal("0.3"), Decimal("0.3"), 1, 60, "بدايتي فرع الفيوم", "y", "Company HQ", "z", "OND"),                # branch -> HQ
    ("1000000003", date(2026, 8, 30), "Qena", "Agouza", Decimal("0.4"), Decimal("0.4"), 1, 75, "Company", "someone", "Company HQ", "z", "OND"),                       # unknown sender city only
    ("1000000004", date(2026, 8, 30), "Qena", "Dishna", Decimal("0.4"), Decimal("0.4"), 1, 75, "Company", "someone", "شركة بدايتي فرع دشنا", "w", "ONP"),             # unknown -> branch
    ("1000000005", date(2026, 8, 31), "Giza", "Giza", Decimal("7.2"), Decimal("6.0"), 2, 100, "Company HQ", "p", "Company HQ", "q", "OND"),                           # HQ -> HQ, heavy, volumetric, 2 pcs
    ("1000000006", date(2026, 8, 31), "Fayoum", "Giza", Decimal("0.2"), Decimal("0.2"), 1, 60, "شركة بدايتي فرع الفيوم", "r", "شركة بدايتي فرع طما", "s", "OND"),     # branch + HQ city conflict on the receiver
]
SHIPMENTS_B = [   # invoice B: 1-3 Sep 2026
    ("2000000001", date(2026, 9, 1), "Giza", "Fayoum", Decimal("1.0"), Decimal("1.0"), 1, 60, "Company HQ", "Hq Person", "شركة بدايتي فرع الفيوم", "x", "OND"),
    ("2000000002", date(2026, 9, 1), "Fayoum", "Agouza", Decimal("0.3"), Decimal("0.3"), 1, 60, "بدايتي فرع الفيوم", "y", "Company HQ", "z", "OND"),
    ("2000000003", date(2026, 9, 2), "Fayoum", "Dishna", Decimal("0.3"), Decimal("0.3"), 1, 65, "بدايتي فرع الفيوم", "y", "شركة بدايتي فرع دشنا", "w", "OND"),           # branch -> branch
    ("2000000004", date(2026, 9, 3), "Giza", "Dishna", Decimal("2.0"), Decimal("2.0"), 1, 65, "Company HQ", HQ_CONTACT, "شركة بدايتي فرع دشنا", "w", "OND"),
]
OTHER = Decimal("0.518")


def _money(x) -> Decimal:
    return Decimal(x).quantize(Decimal("0.01"))


def _lines(rows):
    out = []
    for r in rows:
        base = Decimal(r[7])
        other = _money(base * OTHER)
        net = base + other
        tax = _money(net * Decimal("0.14"))
        out.append({"r": r, "base": base, "other": other, "net": net, "tax": tax, "gross": net + tax})
    return out


@functools.lru_cache(maxsize=None)  # saved workbooks/PDFs embed a timestamp: identical bytes are needed for duplicate-upload tests
def shipments_workbook(bill: str = "1365000001", which: str = "A", adjustment: str = "-0.01", base_bump_awb: str = "", drop_awb: str = "", extra_bill: bool = False) -> bytes:
    rows = SHIPMENTS_A if which == "A" else SHIPMENTS_B
    hdr = ["Bill. Doc.", "Payer", "Name", "Airway Bill No.", "Origin Location", "Destination Location", "Shipper Name", "Shipper Sent By", "Consignee Name",
           "Consignee Address", "Base Charge", "Other Charge", "Net Value", "Tax Amount", "Amount", "Condition Type", "Net weight", "Reference", "Chargeable Weight",
           "Weight unit", "Customer Reference", "Shipper Reference", "Actual weight", "Charge Type", "Billing Type", "Shipper Address", "Shipper City", "Consignee City",
           "Consignee Attention By", "Airwaybill Date"]
    wb = Workbook()
    ws = wb.active
    ws.append(hdr)
    tot = {"base": Decimal(0), "other": Decimal(0), "tax": Decimal(0), "gross": Decimal(0)}
    for ln in _lines(rows):
        r = ln["r"]
        if r[0] == drop_awb:
            continue
        base = ln["base"] + (1 if r[0] == base_bump_awb else 0)
        b = bill if not extra_bill or r[0] != rows[-1][0] else "999"
        ws.append([b, "12345678", "Company", r[0], r[2], r[3], r[8], r[9], r[10], "addr", float(base), float(ln["other"]), float(base + ln["other"] + ln["tax"]), float(ln["tax"]),
                   float(base), "", 0, "ref", float(r[4]), "KG", "", "", float(r[5]), "", "ZDOI", "addr", r[2], r[3], r[11], datetime(2026, 10, 28)])
        for k, v in (("base", base), ("other", ln["other"]), ("tax", ln["tax"]), ("gross", base + ln["other"] + ln["tax"])):
            tot[k] += v
    if adjustment:
        adj = Decimal(adjustment)
        ws.append([bill, "12345678", "Company", "TAX Rounding Diff", "Qena", "Agouza", "x", "x", "x", "x", 0, 0, float(adj), float(adj), 0, "", 0, "ref", 0.1, "KG", "", "", 0.1, "", "ZDOI", "", "", "", "", datetime(2026, 10, 28)])
        tot["tax"] += adj
        tot["gross"] += adj
    ws.append([bill, None, None, None, None, None, None, None, None, None, float(tot["base"]), float(tot["other"]), float(tot["gross"]), float(tot["tax"]), float(tot["base"])])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


@functools.lru_cache(maxsize=None)
def invoice_pdf(bill: str = "1365000001", which: str = "A", adjustment: str = "-0.01", unreadable: bool = False, vat_wrong: bool = False) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    rows = SHIPMENTS_A if which == "A" else SHIPMENTS_B
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(800, A4[1]))
    c.setFont("Helvetica", 8)
    y = A4[1] - 30
    head = ["Domestic Outbound Summary Invoice", f"To: Company Invoice Number: CAI/{bill}-DOI", "Page Page 1 of 1", "Document Date: 09/28/2026", "Credit Terms: 30 Days",
            "Due Date: 10/28/2026", "Customer No. Team Currency", "12345678 Key Customers EGP",
            "S.No HAWB Pick up date Shipper Ref. Origin Destination Prod Weight PCS Base Charge Other Net Amount"]
    for t in head:
        c.drawString(30, y, t)
        y -= 13
    net_tot = vat = Decimal(0)
    for i, ln in enumerate(_lines(rows), 1):
        r = ln["r"]
        c.drawString(30, y, f"{i} {r[0]} {r[1].strftime('%m/%d/%Y')} {r[2]} {r[3]} {r[12]} {r[4]:.3f} KG {r[6]} {ln['base']:.2f} {ln['other']:.2f} {ln['net']:.2f}")
        y -= 12
        c.drawString(30, y, "Operational details: Shipper - x, Receiver - y, addr, " + r[3])
        y -= 14
        net_tot += ln["net"]
        vat += ln["tax"]
    if unreadable:
        c.drawString(30, y, "99 1999999999 08/29/2026 broken line without amounts")
        y -= 14
    vat += Decimal(adjustment or 0)
    if vat_wrong:
        vat += 5
    c.drawString(30, y - 10, f"Total Net Amount: {net_tot:,.2f}")
    c.drawString(30, y - 24, f"VAT 14 % {vat:,.2f}")
    c.drawString(30, y - 38, f"Total Invoice Amount: EGP {net_tot + vat:,.2f}")
    c.save()
    return buf.getvalue()


@functools.lru_cache(maxsize=None)
def scanned_appendix_pdf() -> bytes:
    """An image-only (no text) PDF, like the scanned contract appendix."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.rect(50, 50, 200, 200, fill=1)
    c.showPage()
    c.save()
    return buf.getvalue()
