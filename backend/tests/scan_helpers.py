"""Synthetic scanned documents (no real data): a ruled line-item table drawn on an A4 300-dpi page, slightly rotated,
saved as an image-only PDF - i.e. what a scanner produces."""
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def fonts_available() -> bool:
    return Path(FONT).exists() and shutil.which("tesseract") is not None and shutil.which("pdftoppm") is not None


def make_po_scan(path: Path, rows: list[tuple[str, str, str, str]], total_text: str, title: str = "Purchase Order",
                 angle: float = 0.4) -> Path:
    W, H = 2480, 3508
    im = Image.new("L", (W, H), 255)
    d = ImageDraw.Draw(im)
    big, f, fb = ImageFont.truetype(FONT_BOLD, 80), ImageFont.truetype(FONT, 44), ImageFont.truetype(FONT_BOLD, 44)
    d.text((220, 260), title, font=big, fill=0)
    d.text((220, 400), "Supplier: Test Supplies Ltd", font=f, fill=0)
    xs = [200, 380, 1380, 1680, 2000, 2280]
    heads = ["No", "Description", "Qty", "Unit Price", "Total"]
    y0, hh = 700, 110
    n = len(rows)
    ys = [y0 + i * hh for i in range(n + 3)]  # header + rows + total row
    for y in ys:
        d.line([(xs[0], y), (xs[-1], y)], fill=0, width=4)
    for x in xs:
        d.line([(x, ys[0]), (x, ys[-1])], fill=0, width=4)
    for i, h in enumerate(heads):
        d.text((xs[i] + 20, ys[0] + 28), h, font=fb, fill=0)
    for r, (desc, qty, price, total) in enumerate(rows, start=1):
        y = ys[r] + 28
        d.text((xs[0] + 40, y), str(r), font=f, fill=0)
        d.text((xs[1] + 20, y), desc, font=f, fill=0)
        d.text((xs[2] + 20, y), qty, font=f, fill=0)
        d.text((xs[3] + 20, y), price, font=f, fill=0)
        d.text((xs[4] + 20, y), total, font=f, fill=0)
    yt = ys[n + 1] + 28
    d.text((xs[1] + 20, yt), "Total", font=fb, fill=0)
    d.text((xs[4] + 20, yt), total_text, font=fb, fill=0)
    if angle:
        im = im.rotate(angle, resample=Image.BICUBIC, fillcolor=255)
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, "PDF", resolution=300)
    return path


ROWS = [("Laptop Dell 15", "3", "28100", "84300"), ("Wireless Mouse", "10", "150", "1500"),
        ("HDMI Cable 2m", "20", "95", "1900"), ("UPS 1000VA", "2", "4250.50", "8501.00")]
