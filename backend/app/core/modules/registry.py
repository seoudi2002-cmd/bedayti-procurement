"""Discovers module packages under app/modules/* and validates them. The core never names a module."""
from pathlib import Path

import yaml
from sqlalchemy.orm import Session

from app.core.modules.spec import (
    KpiSpec, ModuleManifest, ModuleSchema, ReportModuleSpec, RuleSpec,
)
from app.models.meta import ReportModule

MODULES_DIR = Path(__file__).resolve().parents[2] / "modules"


class ModuleConfigError(Exception):
    pass


def _load_yaml(path: Path):
    if not path.exists():
        return None
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_module(path: Path) -> ReportModuleSpec:
    try:
        manifest = ModuleManifest(**_load_yaml(path / "module.yaml"))
        schema = ModuleSchema(**_load_yaml(path / "schema.yaml"))
        kpis = [KpiSpec(**k) for k in (_load_yaml(path / "kpis.yaml") or {}).get("kpis", [])]
        rules = [RuleSpec(**r) for r in (_load_yaml(path / "rules.yaml") or {}).get("rules", [])]
    except Exception as exc:  # surface which package is broken
        raise ModuleConfigError(f"Invalid module package '{path.name}': {exc}") from exc
    spec = ReportModuleSpec(manifest=manifest, schema_=schema, kpis=kpis, rules=rules)
    _validate_references(spec)
    if manifest.id != path.name:
        raise ModuleConfigError(f"Module id '{manifest.id}' must match folder name '{path.name}'")
    return spec


def _validate_references(spec: ReportModuleSpec) -> None:
    codes = {k.code for k in spec.kpis}
    if len(codes) != len(spec.kpis):
        raise ModuleConfigError(f"{spec.manifest.id}: duplicate KPI codes")
    for k in spec.kpis:
        for ref in (k.numerator, k.denominator):
            if ref and ref not in codes:
                raise ModuleConfigError(f"{spec.manifest.id}: KPI '{k.code}' references unknown KPI '{ref}'")
    for r in spec.rules:
        if r.kpi and r.kpi not in codes:
            raise ModuleConfigError(f"{spec.manifest.id}: rule '{r.code}' references unknown KPI '{r.kpi}'")


class ModuleRegistry:
    def __init__(self, modules_dir: Path = MODULES_DIR):
        self._modules: dict[str, ReportModuleSpec] = {}
        for pkg in sorted(p for p in modules_dir.iterdir() if (p / "module.yaml").exists()):
            spec = load_module(pkg)
            self._modules[spec.manifest.id] = spec

    def all(self) -> list[ReportModuleSpec]:
        return list(self._modules.values())

    def get(self, module_id: str) -> ReportModuleSpec:
        try:
            return self._modules[module_id]
        except KeyError:
            raise KeyError(f"Unknown module '{module_id}'") from None

    def sync_to_db(self, session: Session) -> None:
        """Upsert module metadata so foreign keys (import_batch.module_id ...) resolve."""
        for spec in self.all():
            m = spec.manifest
            row = session.get(ReportModule, m.id)
            config = {"fact_targets": m.fact_targets, "description": m.description}
            if row is None:
                session.add(ReportModule(id=m.id, name=m.name, version=m.version, category=m.category, config=config))
            else:
                row.name, row.version, row.category, row.config = m.name, m.version, m.category, config
        session.commit()


_registry: ModuleRegistry | None = None


def get_registry() -> ModuleRegistry:
    global _registry
    if _registry is None:
        _registry = ModuleRegistry()
    return _registry
