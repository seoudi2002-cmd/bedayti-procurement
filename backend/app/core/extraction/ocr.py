"""OCR engines. The platform depends on the `OcrEngine` protocol only; Tesseract (Arabic + English) is the
default local engine. Others (cloud OCR, an LLM-vision engine) can be added behind the same interface, but sending
company documents to an external service must be an explicit, separate decision.

Every recognised word keeps its confidence (0-100) and bounding box so that downstream extraction can carry
confidence and a source location for each value.
"""
import csv
import io
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

LANGS = "ara+eng"
# One thread per Tesseract process: parallelism comes from running pages concurrently, and the default OpenMP
# thread pool can stall inside containers.
_ENV = {**os.environ, "OMP_THREAD_LIMIT": "1"}


@dataclass
class Word:
    text: str
    conf: float  # 0-100, -1 when unknown
    left: int
    top: int
    width: int
    height: int
    line_key: tuple = ()

    @property
    def right(self) -> int:
        return self.left + self.width

    @property
    def bottom(self) -> int:
        return self.top + self.height

    @property
    def cx(self) -> float:
        return self.left + self.width / 2

    @property
    def cy(self) -> float:
        return self.top + self.height / 2


@dataclass
class OcrPage:
    words: list[Word] = field(default_factory=list)
    lang: str = LANGS  # language model that produced the best reading of this page
    rotation: int = 0  # degrees the page image was rotated (clockwise) to read upright
    width: int = 0
    height: int = 0

    @property
    def mean_conf(self) -> float:
        good = [w.conf for w in self.words if w.conf >= 0]
        return sum(good) / len(good) if good else 0.0

    def text(self) -> str:
        """Lines in reading order (the page is read right-to-left for Arabic by Tesseract per line)."""
        lines: dict[tuple, list[Word]] = {}
        for w in self.words:
            lines.setdefault(w.line_key, []).append(w)
        return "\n".join(" ".join(w.text for w in ws) for ws in lines.values())


class OcrEngine(Protocol):
    name: str

    def available(self) -> bool: ...

    def ocr_image(self, image_path: Path, psm: int = 6, lang: str = LANGS, whitelist: str | None = None) -> OcrPage: ...

    def detect_rotation(self, image_path: Path) -> int: ...

    def detect_script(self, image_path: Path) -> str: ...


class TesseractEngine:
    name = "tesseract"

    def available(self) -> bool:
        return shutil.which("tesseract") is not None

    def version(self) -> str:  # noqa: D102
        out = subprocess.run(["tesseract", "--version"], capture_output=True, text=True)
        return (out.stdout or out.stderr).splitlines()[0] if (out.stdout or out.stderr) else "unknown"

    def ocr_image(self, image_path: Path, psm: int = 6, lang: str = LANGS, whitelist: str | None = None) -> OcrPage:
        cmd = ["tesseract", str(image_path), "stdout", "-l", lang, "--psm", str(psm), "tsv"]
        if whitelist:
            cmd[-1:-1] = ["-c", f"tessedit_char_whitelist={whitelist}"]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180, env=_ENV)
        words: list[Word] = []
        reader = csv.DictReader(io.StringIO(proc.stdout), delimiter="\t", quoting=csv.QUOTE_NONE)
        page_w = page_h = 0
        for r in reader:
            level = r.get("level")
            if level == "1":
                page_w, page_h = int(r["width"]), int(r["height"])
            if level != "5" or not (r.get("text") or "").strip():
                continue
            words.append(Word(r["text"].strip(), float(r["conf"]), int(r["left"]), int(r["top"]), int(r["width"]),
                              int(r["height"]), (r["block_num"], r["par_num"], r["line_num"])))
        return OcrPage(words=words, width=page_w, height=page_h)

    def _osd(self, image_path: Path) -> tuple[int, float, str]:
        proc = subprocess.run(["tesseract", str(image_path), "stdout", "--psm", "0", "-l", "osd"],
                              capture_output=True, text=True, timeout=120, env=_ENV)
        rot, conf, script = 0, 0.0, ""
        for line in proc.stdout.splitlines():
            if line.startswith("Rotate:"):
                rot = int(line.split(":")[1])
            if line.startswith("Orientation confidence:"):
                conf = float(line.split(":")[1])
            if line.startswith("Script:"):
                script = line.split(":")[1].strip()
        return rot, conf, script

    def detect_rotation(self, image_path: Path) -> int:
        """Degrees (0/90/180/270) to rotate clockwise so the text reads upright; 0 when undecidable."""
        rot, conf, _ = self._osd(image_path)
        return rot if conf >= 2.0 else 0

    def detect_script(self, image_path: Path) -> str:
        return self._osd(image_path)[2]


def default_engine() -> TesseractEngine:
    return TesseractEngine()


def rotate_image(src: Path, degrees: int, dst: Path) -> Path:
    from PIL import Image
    with Image.open(src) as im:
        im.rotate(-degrees, expand=True).save(dst)  # PIL rotates counter-clockwise: negate for clockwise
    return dst


def ocr_page_upright(engine: OcrEngine, image_path: Path, workdir: Path | None = None) -> OcrPage:
    """OCR a page, fixing orientation first (scanned forms are often stored sideways)."""
    work = workdir or Path(tempfile.mkdtemp(prefix="ocr_"))
    rotation = engine.detect_rotation(image_path)
    img0 = image_path if rotation == 0 else rotate_image(image_path, rotation, work / f"{image_path.stem}_r{rotation}.png")
    script = engine.detect_script(img0) if hasattr(engine, "detect_script") else ""
    first, other = ("eng", LANGS) if script == "Latin" else (LANGS, "eng")
    best = engine.ocr_image(img0, lang=first)
    best.rotation, best.lang = rotation, first
    if best.mean_conf < 55:
        alt = engine.ocr_image(img0, lang=other)  # the script guess may be wrong: keep the more legible reading
        alt.rotation, alt.lang = rotation, other
        if alt.mean_conf > best.mean_conf + 5:
            best = alt
    if best.mean_conf < 55 and not rotation:
        # orientation was undecided: try the other orientations and keep the most legible
        for rot in (90, 270, 180):
            img = rotate_image(image_path, rot, work / f"{image_path.stem}_r{rot}.png")
            page = engine.ocr_image(img, lang=best.lang)
            page.rotation, page.lang = rot, best.lang
            if page.mean_conf > best.mean_conf + 8:
                best = page
    return best
