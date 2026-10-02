"""Typed contract for a module package (module.yaml, schema.yaml, kpis.yaml, rules.yaml)."""
from typing import Literal

from pydantic import BaseModel, Field, model_validator

FieldType = Literal["text", "number", "integer", "date", "enum", "bool"]
DimensionName = Literal["branch", "supplier", "category", "item", "cost_center", "asset"]


class FieldSpec(BaseModel):
    name: str
    label: str
    type: FieldType = "text"
    required: bool = False
    dimension: DimensionName | None = None  # resolve against dim_* via entity_alias
    aliases: list[str] = Field(default_factory=list)  # header spellings, English + Arabic
    allowed_values: list[str] = Field(default_factory=list)
    min: float | None = None
    default: str | float | int | None = None
    # computed when absent in the source: {"op": "multiply", "of": ["quantity", "unit_price"]}
    derive: dict | None = None


class ModuleSchema(BaseModel):
    fields: list[FieldSpec]
    # canonical field holding the transaction date; periods are derived from it
    date_field: str
    dayfirst: bool = True
    # fields that identify a source row; repeats are flagged as duplicate_key warnings
    unique_key: list[str] = Field(default_factory=list)
    # optional field derived from date_field when the source has no fiscal-year column
    fiscal_year_field: str | None = None

    @model_validator(mode="after")
    def _check(self):
        names = [f.name for f in self.fields]
        if self.fiscal_year_field and self.fiscal_year_field not in names:
            raise ValueError("fiscal_year_field is not a schema field")
        if any(k not in names for k in self.unique_key):
            raise ValueError("unique_key references unknown field")
        if len(names) != len(set(names)):
            raise ValueError("duplicate field names in schema")
        if self.date_field not in names:
            raise ValueError(f"date_field '{self.date_field}' is not a schema field")
        for f in self.fields:
            if f.derive:
                missing = [n for n in f.derive.get("of", []) if n not in names]
                if missing or f.derive.get("op") != "multiply":
                    raise ValueError(f"invalid derive on '{f.name}'")
        return self

    def field(self, name: str) -> FieldSpec:
        return next(f for f in self.fields if f.name == name)


class KpiSpec(BaseModel):
    code: str
    name: str
    unit: str = ""  # EGP, %, count, EGP/page ...
    format: Literal["currency", "number", "percent", "ratio"] = "number"
    direction: Literal["higher_is_better", "lower_is_better", "neutral"] = "neutral"
    kind: Literal["aggregate", "ratio"] = "aggregate"
    # aggregate
    source: str | None = None  # fact table name, e.g. fact_po_line
    column: str | None = None
    agg: Literal["sum", "avg", "count", "count_distinct", "min", "max"] | None = None
    where: dict[str, str | int | float] = Field(default_factory=dict)
    # ratio of two other KPIs in the same module
    numerator: str | None = None
    denominator: str | None = None
    scale: float = 1.0  # e.g. 100 for percentages

    @model_validator(mode="after")
    def _check(self):
        if self.kind == "aggregate" and not (self.source and self.agg):
            raise ValueError(f"KPI '{self.code}': aggregate needs source and agg")
        if self.kind == "aggregate" and self.agg != "count" and not self.column:
            raise ValueError(f"KPI '{self.code}': aggregate needs a column")
        if self.kind == "ratio" and not (self.numerator and self.denominator):
            raise ValueError(f"KPI '{self.code}': ratio needs numerator and denominator")
        return self


class RuleSpec(BaseModel):
    """Declarative insight rule. Evaluated by the insight engine (Phase 4)."""

    code: str
    kind: Literal["period_change", "peer_outlier", "threshold", "price_variance", "concentration"]
    kpi: str | None = None
    severity: Literal["info", "warning", "critical"] = "warning"
    params: dict = Field(default_factory=dict)
    title: str


class DocumentTypeSpec(BaseModel):
    """A document kind in the module's end-to-end workflow (requisition → ... → payment)."""

    code: str
    label: str
    label_ar: str = ""
    stage: int  # position in the lifecycle; used to derive a case's current stage
    required: bool = False  # expected for a complete file; drives "missing documents" checks


class ModuleManifest(BaseModel):
    id: str
    name: str
    version: str = "0.1.0"
    category: str
    description: str = ""
    period_grain: Literal["month"] = "month"
    fact_targets: list[str] = Field(default_factory=list)  # tables the loader writes to
    document_types: list[DocumentTypeSpec] = Field(default_factory=list)
    # unmatched names per dimension: "create" a new dim row, or hold the row for "review"
    entity_policy: dict[str, Literal["create", "review"]] = Field(default_factory=dict)


class ReportModuleSpec(BaseModel):
    manifest: ModuleManifest
    schema_: ModuleSchema
    kpis: list[KpiSpec] = Field(default_factory=list)
    rules: list[RuleSpec] = Field(default_factory=list)

    def kpi(self, code: str) -> KpiSpec:
        for k in self.kpis:
            if k.code == code:
                return k
        raise KeyError(code)
