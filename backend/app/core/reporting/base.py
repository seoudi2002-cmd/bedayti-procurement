"""Exporter contract (Phase 5). Excel, PDF and PowerPoint exporters implement this and consume the
same report model (sections of KPI tables, charts, insights), so a new format never touches modules."""
from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class ReportSection:
    title: str
    kpis: list[dict] = field(default_factory=list)
    tables: list[dict] = field(default_factory=list)
    charts: list[dict] = field(default_factory=list)
    insights: list[dict] = field(default_factory=list)
    commentary: str | None = None


@dataclass
class ReportModel:
    title: str
    period_label: str
    sections: list[ReportSection]
    executive_summary: str | None = None


class Exporter(Protocol):
    extension: str

    def render(self, report: ReportModel) -> bytes: ...
