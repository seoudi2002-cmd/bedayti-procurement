"""PDF exporter (reportlab). Consumes a ReportModel; Arabic is shaped and laid out right-to-left."""
import io
import re
from decimal import Decimal

import matplotlib as mpl
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.core.reporting.base import ReportModel
from app.core.reporting.charts import render_chart

extension = "pdf"
_FONTS = mpl.get_data_path() + "/fonts/ttf/"
_ARABIC = re.compile("[؀-ۿ]")
BLUE, INK, INK2, MUTED, GRID, CARD = colors.HexColor("#2a78d6"), colors.HexColor("#0b0b0b"), colors.HexColor("#52514e"), \
    colors.HexColor("#898781"), colors.HexColor("#e1e0d9"), colors.HexColor("#f4f6fa")
SEV = {"critical": colors.HexColor("#d03b3b"), "warning": colors.HexColor("#c98500"), "info": colors.HexColor("#256abf")}
_registered = False


def _register():
    global _registered
    if not _registered:
        pdfmetrics.registerFont(TTFont("DJ", _FONTS + "DejaVuSans.ttf"))
        pdfmetrics.registerFont(TTFont("DJ-B", _FONTS + "DejaVuSans-Bold.ttf"))
        pdfmetrics.registerFontFamily("DJ", normal="DJ", bold="DJ-B", italic="DJ", boldItalic="DJ-B")
        _registered = True


def fmt(v, kind: str) -> str:
    if v is None or v == "":
        return "—" if kind != "text" else ""
    try:
        if kind == "money":
            return f"{Decimal(str(v)):,.0f}"
        if kind == "smoney":
            return f"{Decimal(str(v)):+,.0f}"
        if kind == "money3":
            return f"{Decimal(str(v)):,.3f}"
        if kind == "num":
            return f"{Decimal(str(v)):,.2f}"
        if kind == "snum":
            return f"{Decimal(str(v)):+,.2f}"
        if kind == "pct":
            return f"{float(v):.1f}%"
        if kind == "spct":
            return f"{float(v):+.1f}%"
        if kind == "int":
            return f"{int(v):,}"
    except (ValueError, ArithmeticError):
        pass
    return str(v)


def _visual(text: str) -> str:
    import arabic_reshaper
    from bidi.algorithm import get_display
    return get_display(arabic_reshaper.reshape(text))


def rtl_markup(text, font: str, size: float, width: float | None) -> str:
    """Arabic needs shaping + bidi on each *line*: wrap the logical text by measured width first, then convert every
    line to visual order (reportlab's own RTL wrapping does not shape or reorder Arabic letters)."""
    s = "" if text is None else str(text)
    if not _ARABIC.search(s):
        return _esc(s)
    if not width:
        return _esc(_visual(s))
    lines, cur = [], ""
    for word in s.split():
        trial = (cur + " " + word).strip()
        if cur and pdfmetrics.stringWidth(_visual(trial), font, size) > width:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    lines.append(cur)
    return "<br/>".join(_esc(_visual(line)) for line in lines)


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class PdfExporter:
    extension = "pdf"

    def render(self, report: ReportModel) -> bytes:
        _register()
        lang = report.lang
        rtl = lang == "ar"

        def sh(text, font="DJ", size=8.5, width=None) -> str:
            return rtl_markup(text, font, size, width)  # also shapes Arabic names inside English reports

        base = dict(fontName="DJ", fontSize=8.5, leading=12, textColor=INK, alignment=TA_RIGHT if rtl else TA_LEFT)
        st = {
            "body": ParagraphStyle("body", **base),
            "small": ParagraphStyle("small", **{**base, "fontSize": 7.5, "leading": 10, "textColor": INK2}),
            "cell": ParagraphStyle("cell", **{**base, "fontSize": 7.5, "leading": 9.5}),
            "cellb": ParagraphStyle("cellb", **{**base, "fontSize": 7.5, "leading": 9.5, "fontName": "DJ-B", "textColor": colors.white}),
            "h1": ParagraphStyle("h1", **{**base, "fontName": "DJ-B", "fontSize": 19, "leading": 24}),
            "h2": ParagraphStyle("h2", **{**base, "fontName": "DJ-B", "fontSize": 13, "leading": 17, "textColor": BLUE, "spaceBefore": 4, "spaceAfter": 5, "keepWithNext": 1}),
            "h3": ParagraphStyle("h3", **{**base, "fontName": "DJ-B", "fontSize": 9.5, "leading": 13, "spaceBefore": 8, "spaceAfter": 3, "keepWithNext": 1}),
            "kv": ParagraphStyle("kv", **{**base, "fontName": "DJ-B", "fontSize": 13, "leading": 16}),
            "kl": ParagraphStyle("kl", **{**base, "fontSize": 7.5, "textColor": INK2}),
        }
        avail = A4[0] - 2 * 16 * mm
        P = lambda text, style: Paragraph(sh(text, "DJ-B" if style.startswith("h") else "DJ", st[style].fontSize, avail), st[style])  # noqa: E731
        buf = io.BytesIO()
        W, H = A4
        margin = 16 * mm
        doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=margin, rightMargin=margin, topMargin=18 * mm, bottomMargin=16 * mm,
                                title=report.title, author="Procurement & Administrative Intelligence Platform")

        def footer(canvas, d):
            canvas.saveState()
            canvas.setFont("DJ", 7)
            canvas.setFillColor(MUTED)
            left = f"{report.meta.get('file_name', '')} · sha256 {report.meta.get('file_hash', '')[:10]} · {report.meta.get('generated_at', '')}"
            canvas.drawString(margin, 9 * mm, left)
            canvas.drawRightString(W - margin, 9 * mm, str(d.page))
            canvas.setStrokeColor(GRID)
            canvas.line(margin, 12 * mm, W - margin, 12 * mm)
            canvas.restoreState()

        story: list = [P(report.title, "h1"), Spacer(1, 2 * mm)]
        if report.subtitle:
            story.append(P(report.subtitle, "small"))
        if report.period_label:
            story.append(P(report.period_label, "small"))
        story.append(Spacer(1, 4 * mm))

        for si, sec in enumerate(report.sections):
            story.append(P(sec.title, "h2"))
            if sec.kpis:
                story.append(self._kpi_grid(sec.kpis, avail, st, sh, rtl))
                story.append(Spacer(1, 4 * mm))
            ins = [i for i in sec.insights]
            for i in ins:
                col = SEV.get(i.get("severity", "info"), INK2)
                story.append(Paragraph(f'<font color="{col.hexval().replace("0x", "#")}">●</font> ' + sh(i["text"], "DJ", 8.5, avail - 14), st["body"]))
                story.append(Spacer(1, 1.5 * mm))
            for ch in sec.charts:
                try:
                    png = render_chart(ch, lang)
                except Exception:  # a chart must never block the report
                    continue
                story.append(KeepTogether([Image(io.BytesIO(png), width=avail, height=avail * self._ratio(png))]))
                story.append(Spacer(1, 2 * mm))
            for tb in sec.tables:
                story.extend(self._table(tb, avail, st, sh, rtl, lang))
            if sec.commentary:
                story.append(P(sec.commentary, "body"))
            story.append(Spacer(1, 3 * mm))
            if sec.title and si in (0, 2, 4) and si != len(report.sections) - 1:
                story.append(PageBreak())
        doc.build(story, onFirstPage=footer, onLaterPages=footer)
        return buf.getvalue()

    @staticmethod
    def _ratio(png: bytes) -> float:
        from PIL import Image as PILImage
        im = PILImage.open(io.BytesIO(png))
        return im.height / im.width

    def _kpi_grid(self, kpis, avail, st, sh, rtl):
        per_row = 4
        cells = []
        for k in kpis:
            tone = {"up": "#d03b3b", "down": "#256abf"}.get(k.get("tone"), "#52514e")
            val = k["value"]
            size = 13 if len(str(val)) <= 14 else 9.5
            cw = avail / per_row - 10
            sub = f'<font color="{tone}" size="7.5">{sh(k.get("sub", ""), "DJ", 7.5, cw)}</font>' if k.get("sub") else ""
            cells.append([Paragraph(sh(k["label"], "DJ", 7.5, cw), st["kl"]),
                          Paragraph(f'<font size="{size}"><b>{sh(val, "DJ-B", size, cw)}</b></font>', st["body"]),
                          Paragraph(sub, st["body"])])
        rows = []
        for i in range(0, len(cells), per_row):
            chunk = cells[i:i + per_row]
            chunk += [[Paragraph("", st["body"])] * 3] * (per_row - len(chunk))
            if rtl:
                chunk = chunk[::-1]
            rows.append(chunk)
        w = avail / per_row
        t = Table(rows, colWidths=[w] * per_row)
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), CARD), ("BOX", (0, 0), (-1, -1), 2, colors.white),
                               ("INNERGRID", (0, 0), (-1, -1), 2, colors.white), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                               ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
        return t

    def _table(self, tb, avail, st, sh, rtl, lang):
        cols = tb["columns"]
        if tb.get("pdf_cols") and len(cols) > tb["pdf_cols"] + 2:  # keep the label, the first N value columns and the total
            cols = cols[: tb["pdf_cols"] + 1] + cols[-1:]
        if tb.get("pdf_skip"):  # columns kept for Excel/the dashboard but left out of the printed page
            cols = [x for x in cols if x["key"] not in tb["pdf_skip"]]
        rows = tb["rows"][: tb.get("pdf_rows", 15)]
        if not rows:
            return []
        out = [Paragraph(sh(tb["title"], "DJ-B", 9.5, avail), st["h3"])]
        # width weights: text columns by their longest cell (capped), numeric columns narrow
        weights = []
        for c in cols:
            if c["fmt"] == "text":
                mx = max([len(str(r.get(c["key"]) or "")) for r in rows] + [len(c["label"])])
                weights.append(min(max(mx, 8), 46))
            else:
                weights.append(max(11, len(c["label"]) * 0.7))
        tot = sum(weights)
        widths = [avail * w / tot for w in weights]
        order = list(range(len(cols)))
        if rtl:
            order = order[::-1]
        header = [Paragraph(sh(cols[i]["label"], "DJ-B", 7.5, widths[i] - 6), st["cellb"]) for i in order]
        data = [header]
        for r in rows:
            row = []
            for i in order:
                c = cols[i]
                txt = fmt(r.get(c["key"]), c["fmt"])
                style = st["cell"]
                row.append(Paragraph(sh(txt, "DJ", 7.5, widths[i] - 6), style))
            data.append(row)
        t = Table(data, colWidths=[widths[i] for i in order], repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), BLUE), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, CARD]),
            ("LINEBELOW", (0, 0), (-1, -1), 0.25, GRID), ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5)]))
        out = [KeepTogether([out[0], t])] if len(rows) <= 22 else out + [t]
        extra = len(tb["rows"]) - len(rows)
        if extra > 0:
            out.append(Paragraph(sh(("… +%d" % extra) + (" (الباقي في ملف Excel)" if lang == "ar" else " more (full list in the Excel file)"), "DJ", 7.5, avail), st["small"]))
        out.append(Spacer(1, 2 * mm))
        return out
