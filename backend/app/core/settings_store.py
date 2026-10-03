"""System settings stored in the database (app_setting), with code-shipped defaults. Changing a setting never
requires a code change or a redeploy; every change records who made it."""
from pathlib import Path

import yaml
from sqlalchemy.orm import Session

from app.models.analysis import AppSetting

MODULES = Path(__file__).resolve().parents[1] / "modules"
# threshold defaults shipped with each analysis module (initial values only; the effective ones live in app_setting)
DEFAULTS_FILES = {"custody": MODULES / "custody_analysis" / "thresholds.yaml", "copier": MODULES / "copier_analysis" / "thresholds.yaml",
                  "aramex": MODULES / "aramex_analysis" / "thresholds.yaml",
                  "procurement": MODULES / "procurement_analysis" / "thresholds.yaml", "rent": MODULES / "rent_analysis" / "thresholds.yaml",
                  "vehicles": MODULES / "vehicle_analysis" / "thresholds.yaml", "overtime": MODULES / "overtime_analysis" / "thresholds.yaml",
                  "custody_advances": MODULES / "custody_analysis" / "advances_thresholds.yaml"}
STRUCT_DEFAULTS = {"copier.paper": MODULES / "copier_analysis" / "paper_defaults.yaml", "aramex.parties": MODULES / "aramex_analysis" / "parties_defaults.yaml",
                   "aramex.rates": MODULES / "aramex_analysis" / "rates_defaults.yaml",
                   "vehicles.plates": MODULES / "vehicle_analysis" / "plates_defaults.yaml"}
KNOWN_KEYS = {"custody.thresholds", "custody.display_taxonomy", "custody.branch_key", "copier.thresholds", "copier.paper", "aramex.thresholds", "procurement.thresholds", "custody_advances.thresholds", "rent.thresholds", "vehicles.thresholds", "overtime.thresholds",
              "aramex.parties", "aramex.rates", "vehicles.plates"}


def default_thresholds(module: str = "custody") -> dict:
    return yaml.safe_load(DEFAULTS_FILES[module].read_text(encoding="utf-8"))


def custody_default_thresholds() -> dict:  # kept for existing callers
    return default_thresholds("custody")


def get_setting(session: Session, key: str, default=None):
    row = session.get(AppSetting, key)
    return row.value if row else default


def set_setting(session: Session, key: str, value, user: str | None) -> None:
    row = session.get(AppSetting, key)
    if row is None:
        session.add(AppSetting(key=key, value=value, updated_by=user))
    else:
        row.value, row.updated_by = value, user
    session.commit()


def effective_thresholds(session: Session, module: str = "custody") -> tuple[dict, dict]:
    """(effective values, {name: 'default' | 'custom'})."""
    defaults = default_thresholds(module)
    custom = get_setting(session, f"{module}.thresholds", {}) or {}
    eff = {**defaults, **{k: v for k, v in custom.items() if k in defaults}}
    return eff, {k: ("custom" if k in custom and k in defaults and custom[k] != defaults[k] else "default") for k in defaults}


def validate_thresholds(values: dict, module: str = "custody") -> dict:
    defaults = default_thresholds(module)
    unknown = [k for k in values if k not in defaults]
    if unknown:
        raise ValueError(f"Unknown threshold(s): {', '.join(unknown)}")
    for k, v in values.items():
        if isinstance(v, bool) or not isinstance(v, (int, float)) or v < 0:
            raise ValueError(f"Threshold '{k}' must be a non-negative number")
    return values


def effective_paper(session: Session) -> tuple[dict, dict]:
    """Paper parameters (carton size, sheets per page, price windows): (effective values, {name: 'default' | 'custom'})."""
    from app.modules.copier_analysis.paper import default_paper_params
    defaults = default_paper_params()
    custom = get_setting(session, "copier.paper", {}) or {}
    eff = {**defaults, **{k: v for k, v in custom.items() if k in defaults}}
    return eff, {k: ("custom" if k in custom and custom[k] != defaults[k] else "default") for k in defaults}


def effective_struct(session: Session, key: str) -> tuple[dict, dict]:
    """A structured (non-threshold) setting such as aramex.parties: (effective values, {name: 'default' | 'custom'})."""
    defaults = yaml.safe_load(STRUCT_DEFAULTS[key].read_text(encoding="utf-8"))
    custom = get_setting(session, key, {}) or {}
    eff = {**defaults, **{k: v for k, v in custom.items() if k in defaults}}
    return eff, {k: ("custom" if k in custom and custom[k] != defaults[k] else "default") for k in defaults}


def struct_defaults(key: str) -> dict:
    return yaml.safe_load(STRUCT_DEFAULTS[key].read_text(encoding="utf-8"))
