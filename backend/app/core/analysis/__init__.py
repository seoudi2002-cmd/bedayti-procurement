"""Analysis-module framework.

Every management-analysis module (custody, copiers, later printing/paper/rent/vehicles/...) plugs into the same
platform surface by providing an *adapter*: ingest an uploaded file, list its items, build a ReportModel for an item
(with optional filters). The generic API, the dashboard shell and the PDF/Excel exporters know nothing about a module.
"""
from dataclasses import dataclass, field
from typing import Protocol

from sqlalchemy.orm import Session

from app.core.reporting.base import ReportModel


class AnalysisError(Exception):
    """A user-facing problem (maps to HTTP 4xx): .status and .detail."""

    def __init__(self, status: int, detail):
        super().__init__(str(detail))
        self.status, self.detail = status, detail


@dataclass
class UploadResult:
    item_id: str | int
    meta: dict
    status: int = 201  # 202 when the file is still being processed in the background
    background: object | None = None  # callable run after the response (e.g. OCR)


@dataclass
class ModuleInfo:
    key: str                  # URL segment: /api/analysis/<key>/...
    module_id: str            # report_module id / package folder
    label: dict               # {"ar":..., "en":...}
    accepts: tuple            # accepted upload extensions
    filters: dict = field(default_factory=dict)   # filter key -> query parameter, e.g. {"periods": "period"}
    upload_hint: dict = field(default_factory=dict)
    thresholds_key: str | None = None


class AnalysisAdapter(Protocol):
    info: ModuleInfo

    def ingest(self, session: Session, content: bytes, filename: str, user: str | None, options: dict) -> UploadResult: ...
    def list_items(self, session: Session) -> list[dict]: ...
    def item_meta(self, session: Session, item_id: str, admin: bool) -> dict: ...
    def delete_item(self, session: Session, item_id: str) -> None: ...
    def build(self, session: Session, item_id: str, lang: str, admin: bool, filters: dict) -> tuple[ReportModel, dict]: ...
    def api_analysis(self, analysis: dict) -> dict: ...
