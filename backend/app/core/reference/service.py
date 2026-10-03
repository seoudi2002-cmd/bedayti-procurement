"""Reference library: files the owner supplies are kept as versioned reference sources for the whole system, not analysed once.

* asset register (xlsx): stored as received, one row per asset, profile + observations + difference from the previous version;
* documents (regulations, annual report, ... as PDF / Word): the original is stored untouched and its text is read (native text or OCR) by the
  existing extraction job; the page texts stay available as reference. Nothing is built on them here.
A new version never replaces an earlier one; the current version is the one with the latest «as of» date (upload order breaks ties)."""
import hashlib
from datetime import date
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.extraction import service as extraction
from app.core.reference import assets
from app.models import AssetRegisterRow, ExtractedPage, ExtractionJob, ReferenceSource

KINDS = ("asset_register", "regulation", "annual_report", "other")
DEFAULT_SERIES = {"asset_register": "asset_register"}


class ReferenceError(Exception):
    def __init__(self, status: int, detail):
        super().__init__(str(detail))
        self.status, self.detail = status, detail


def _digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _store(content: bytes, filename: str, digest: str) -> str:
    d = Path(get_settings().upload_dir) / "reference"
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{digest[:16]}{Path(filename).suffix.lower()}"
    path.write_bytes(content)
    return str(path)


def _refresh_current(session: Session, series: str) -> None:
    vs = list(session.scalars(select(ReferenceSource).where(ReferenceSource.series_key == series)))
    best = max(vs, key=lambda v: (v.as_of_date or date.min, v.version_no))
    for v in vs:
        v.is_current = v is best
    session.commit()


def _next_version(session: Session, series: str) -> int:
    return (session.scalar(select(func.max(ReferenceSource.version_no)).where(ReferenceSource.series_key == series)) or 0) + 1


def register(session: Session, content: bytes, filename: str, user: str | None, kind: str | None = None, series: str | None = None, title: str | None = None,
             as_of: date | None = None, notes: str | None = None) -> ReferenceSource:
    name = filename.lower()
    if kind is None:
        kind = "asset_register" if name.endswith((".xlsx", ".xlsm")) and assets.is_asset_register(content) else None
    if kind not in KINDS:
        raise ReferenceError(422, f"State the kind of this reference file ({', '.join(KINDS)}); an Excel file is recognised as an asset register by its columns")
    digest = _digest(content)
    dup = session.scalar(select(ReferenceSource).where(ReferenceSource.kind == kind, ReferenceSource.file_hash == digest))
    if dup:
        raise ReferenceError(409, {"message": f"This exact file is already stored (reference {dup.id}, version {dup.version_no})", "id": dup.id})
    if kind == "asset_register":
        return _register_assets(session, content, filename, user, series or "asset_register", title, as_of, notes, digest)
    if not name.endswith((".pdf", ".docx")):
        raise ReferenceError(400, "Documents are stored as PDF (scanned or native) or Word (.docx)")
    if not series:
        raise ReferenceError(422, "State the series this document belongs to (e.g. admin_regulation, procurement_regulation, annual_report) so later versions are kept together")
    try:
        job = extraction.create_job(session, filename, content, user)
    except extraction.ExtractionError as exc:
        raise ReferenceError(400, str(exc)) from exc
    src = ReferenceSource(kind=kind, series_key=series, title=title or Path(filename).stem, version_no=_next_version(session, series), as_of_date=as_of,
                          as_of_source="uploader" if as_of else "none", file_name=Path(filename).name, file_hash=digest, storage_path=_store(content, filename, digest),
                          file_id=job.file_id, job_id=job.id, status="processing", uploaded_by=user, notes=notes, summary={})
    session.add(src)
    session.commit()
    _refresh_current(session, series)
    return src


def _register_assets(session, content, filename, user, series, title, as_of, notes, digest) -> ReferenceSource:
    try:
        parsed = assets.parse_assets(content)
    except assets.UnrecognisedAssetRegister as exc:
        raise ReferenceError(422, str(exc)) from exc
    prof = assets.profile(parsed)
    file_as_of = date.fromisoformat(prof["current_period"]) if prof["current_period"] else None
    prev = session.scalar(select(ReferenceSource).where(ReferenceSource.series_key == series).order_by(ReferenceSource.version_no.desc()))
    src = ReferenceSource(kind="asset_register", series_key=series, title=title or "Asset register", version_no=_next_version(session, series), as_of_date=as_of or file_as_of,
                          as_of_source="uploader" if as_of else ("file" if file_as_of else "none"), file_name=Path(filename).name, file_hash=digest,
                          storage_path=_store(content, filename, digest), status="ready", rows_count=len(parsed.rows), uploaded_by=user, notes=notes, summary=prof)
    session.add(src)
    session.flush()
    for r in parsed.rows:
        session.add(AssetRegisterRow(source_id=src.id, **r))
    if prev is not None:
        old: dict[str, list] = {}
        for x in session.scalars(select(AssetRegisterRow).where(AssetRegisterRow.source_id == prev.id)):
            old.setdefault(x.asset_number, []).append({f: getattr(x, f) for f in ("description", "location_text", "major_category", "category_segment", "cost", "net_book_value", "current_units", "date_retired")})
        new: dict[str, list] = {}
        for r in parsed.rows:
            new.setdefault(r["asset_number"], []).append(r)
        d = assets.diff(old, new)
        d["previous_version"], d["previous_as_of"] = prev.version_no, prev.as_of_date.isoformat() if prev.as_of_date else None
        src.summary = {**prof, "diff_vs_previous": d}
    session.commit()
    _refresh_current(session, series)
    return src


def finalize_document(session: Session, source_id: int) -> ReferenceSource:
    """Called when the text job has finished: records page counts and reading quality; marks the version ready (or failed)."""
    src = session.get(ReferenceSource, source_id)
    job = session.get(ExtractionJob, src.job_id) if src.job_id else None
    if job is None or job.status in ("queued", "running"):
        return src
    if job.status == "failed":
        src.status, src.summary = "failed", {**(src.summary or {}), "error": (job.error or "")[:300]}
        session.commit()
        return src
    pages = list(session.scalars(select(ExtractedPage).where(ExtractedPage.job_id == job.id).order_by(ExtractedPage.page_no)))
    confs = [float(p.mean_confidence) for p in pages if p.mean_confidence is not None]
    src.rows_count = len(pages)
    src.status = "ready"
    src.summary = {**(src.summary or {}), "pages": len(pages), "text_sources": {k: sum(1 for p in pages if p.text_source == k) for k in {p.text_source for p in pages}},
                   "words": sum(p.word_count for p in pages), "mean_confidence": round(sum(confs) / len(confs), 3) if confs else None,
                   "low_confidence_pages": [p.page_no for p in pages if p.mean_confidence is not None and float(p.mean_confidence) < 0.5][:60],
                   "empty_pages": [p.page_no for p in pages if p.word_count == 0][:60]}
    session.commit()
    return src


def process_document_job(session: Session, source_id: int) -> None:
    """Background task: read the document (native text / OCR) with the existing job, then finalise."""
    src = session.get(ReferenceSource, source_id)
    try:
        extraction.run_job(session, src.job_id)
    except Exception as exc:  # reading must never take the service down
        src.status, src.summary = "failed", {**(src.summary or {}), "error": str(exc)[:300]}
        session.commit()
        return
    finalize_document(session, source_id)


def meta(src: ReferenceSource, detail: bool = False) -> dict:
    out = {"id": src.id, "kind": src.kind, "series": src.series_key, "title": src.title, "version": src.version_no, "current": src.is_current,
           "as_of": src.as_of_date.isoformat() if src.as_of_date else None, "as_of_source": src.as_of_source, "file_name": src.file_name, "status": src.status,
           "rows": src.rows_count, "uploaded_by": src.uploaded_by, "uploaded_at": src.created_at.isoformat() if src.created_at else None, "notes": src.notes}
    if detail:
        out["summary"] = src.summary
    return out
