"""Typed contract for a module package (module.yaml, schema.yaml, kpis.yaml, rules.yaml)."""
from typing import Literal

from pydantic import BaseModel, Field, model_validator

FieldType = Literal["text", "number", "integer", "date", "enum", "bool"]
DimensionName = Literal["branch", "supplier", "category", "item", "cost_center", "asset", "department"]


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
    # source value -> canonical value (observed categorical spellings); unknown values are flagged, not guessed
    value_map: dict[str, str] = Field(default_factory=dict)
    # "reject": a bad value rejects the row. "flag": keep the row, store NULL, raise an issue (the raw text
    # stays in raw_row.payload). Use "flag" where a row is still valuable with one bad cell.
    on_invalid: Literal["reject", "flag"] = "reject"


class FillDownSpec(BaseModel):
    """Merged cells arrive as one value followed by blanks. `reset_on` stops a value leaking into the next group."""

    field: str
    reset_on: str | None = None


class RowFilterSpec(BaseModel):
    """Keep only rows whose raw `field` matches `regex`; the rest are recorded as skipped (e.g. subtotal rows)."""

    field: str
    regex: str


class ModuleSchema(BaseModel):
    fields: list[FieldSpec]
    # canonical field holding the transaction date; periods are derived from it (None for master data)
    date_field: str | None = None
    dayfirst: bool = True
    # layout hints for the reader
    sheet: str | None = None  # preferred sheet name when the workbook has several
    header_row: int | None = None
    row_filter: RowFilterSpec | None = None
    fill_down: list[FillDownSpec] = Field(default_factory=list)
    # dates outside [plausible_from, today + plausible_days_ahead] are treated as invalid
    plausible_from: str = "2015-01-01"
    plausible_days_ahead: int = 400
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
        if self.date_field is not None and self.date_field not in names:
            raise ValueError(f"date_field '{self.date_field}' is not a schema field")
        for fd in self.fill_down:
            if fd.field not in names or (fd.reset_on and fd.reset_on not in names):
                raise ValueError("fill_down references unknown field")
        if self.row_filter and self.row_filter.field not in names:
            raise ValueError("row_filter references unknown field")
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
    where_not_null: list[str] = Field(default_factory=list)  # only rows where these columns are known
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


class ProfileSpec(BaseModel):
    """An alternative layout of the same module's data (e.g. header-level register vs line-level export)."""

    code: str
    label: str
    description: str = ""


class ModuleManifest(BaseModel):
    id: str
    name: str
    version: str = "0.1.0"
    category: str
    description: str = ""
    period_grain: Literal["month"] = "month"
    fact_targets: list[str] = Field(default_factory=list)  # tables the loader writes to
    document_types: list[DocumentTypeSpec] = Field(default_factory=list)
    profiles: list[ProfileSpec] = Field(default_factory=list)  # each needs profiles/<code>.yaml
    # True for modules holding personal data: their endpoints require the admin role
    contains_personal_data: bool = False
    # unmatched names per dimension: "create" a new dim row, or hold the row for "review"
    entity_policy: dict[str, Literal["create", "review"]] = Field(default_factory=dict)


class ReportModuleSpec(BaseModel):
    manifest: ModuleManifest
    schema_: ModuleSchema
    profile_schemas: dict[str, ModuleSchema] = Field(default_factory=dict)

    def schema_for(self, profile: str | None) -> ModuleSchema:
        if profile in (None, "", "default"):
            return self.schema_
        try:
            return self.profile_schemas[profile]
        except KeyError:
            raise KeyError(f"Module '{self.manifest.id}' has no profile '{profile}'") from None

    kpis: list[KpiSpec] = Field(default_factory=list)
    rules: list[RuleSpec] = Field(default_factory=list)

    def kpi(self, code: str) -> KpiSpec:
        for k in self.kpis:
            if k.code == code:
                return k
        raise KeyError(code)
