"""PDF access: page images (poppler) and the native text layer. Originals are only read, never changed."""
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


class PdfToolsMissing(RuntimeError):
    pass


def require_poppler() -> None:
    if shutil.which("pdftoppm") is None or shutil.which("pdftotext") is None:
        raise PdfToolsMissing("poppler-utils (pdftoppm/pdftotext) is required for PDF extraction")


def page_count(pdf: Path) -> int:
    out = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout
    for line in out.splitlines():
        if line.startswith("Pages:"):
            return int(line.split(":")[1])
    return 0


def native_text(pdf: Path, page: int) -> str:
    out = subprocess.run(["pdftotext", "-f", str(page), "-l", str(page), "-layout", str(pdf), "-"],
                         capture_output=True, text=True)
    return out.stdout


def render_page(pdf: Path, page: int, out_dir: Path, dpi: int = 300) -> Path:
    require_poppler()
    prefix = out_dir / f"p{page:03d}"
    subprocess.run(["pdftoppm", "-f", str(page), "-l", str(page), "-r", str(dpi), "-png", "-gray", str(pdf), str(prefix)],
                   check=True, capture_output=True)
    matches = sorted(out_dir.glob(f"p{page:03d}-*.png"))
    if not matches:
        raise RuntimeError(f"could not render page {page}")
    return matches[0]


@dataclass
class PageText:
    page: int
    text: str
    is_native: bool  # True when the PDF carries a usable text layer


def has_text_layer(text: str, min_chars: int = 40) -> bool:
    return len("".join(text.split())) >= min_chars
