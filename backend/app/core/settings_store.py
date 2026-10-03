"""System settings stored in the database (app_setting), with code-shipped defaults. Changing a setting never
requires a code change or a redeploy; every change records who made it."""
from pathlib import Path

import yaml
from sqlalchemy.orm import Session

from app.models.analysis import AppSetting

CUSTODY_DEFAULTS_FILE = Path(__file__).resolve().parents[1] / "modules" / "custody_analysis" / "thresholds.yaml"

# key -> (default factory, validator)
KNOWN_KEYS = {"custody.thresholds", "custody.display_taxonomy", "custody.branch_key"}


def custody_default_thresholds() -> dict:
    return yaml.safe_load(CUSTODY_DEFAULTS_FILE.read_text(encoding="utf-8"))


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


def effective_thresholds(session: Session) -> tuple[dict, dict]:
    """(effective values, {name: 'default' | 'custom'})."""
    defaults = custody_default_thresholds()
    custom = get_setting(session, "custody.thresholds", {}) or {}
    eff = {**defaults, **{k: v for k, v in custom.items() if k in defaults}}
    return eff, {k: ("custom" if k in custom and k in defaults and custom[k] != defaults[k] else "default") for k in defaults}


def validate_thresholds(values: dict) -> dict:
    defaults = custody_default_thresholds()
    unknown = [k for k in values if k not in defaults]
    if unknown:
        raise ValueError(f"Unknown threshold(s): {', '.join(unknown)}")
    for k, v in values.items():
        if isinstance(v, bool) or not isinstance(v, (int, float)) or v < 0:
            raise ValueError(f"Threshold '{k}' must be a non-negative number")
    return values
