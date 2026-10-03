"""Validation of the Aramex structured settings (parties / Head Office rules, contract rate card)."""
from app.core.settings_store import struct_defaults


def _strings(v, name):
    if not isinstance(v, list) or not all(isinstance(x, str) and x.strip() for x in v):
        raise ValueError(f"'{name}' must be a list of non-empty texts")


def validate_parties(values: dict) -> dict:
    base = struct_defaults("aramex.parties")
    unknown = [k for k in values if k not in base]
    if unknown:
        raise ValueError(f"Unknown setting(s): {', '.join(unknown)}")
    for k, v in values.items():
        _strings(v, k)
    return values


def validate_rates(values: dict) -> dict:
    base = struct_defaults("aramex.rates")
    unknown = [k for k in values if k not in base]
    if unknown:
        raise ValueError(f"Unknown setting(s): {', '.join(unknown)}")
    for k, v in values.items():
        if not isinstance(v, list) or any(isinstance(x, bool) or not isinstance(x, (int, float)) or x <= 0 for x in v):
            raise ValueError(f"'{k}' must be a list of positive numbers")
    return values
