"""Validation of the vehicles.plates setting (approved alias spellings)."""
from app.core.settings_store import struct_defaults


def validate_plates(values: dict) -> dict:
    base = struct_defaults("vehicles.plates")
    unknown = [k for k in values if k not in base]
    if unknown:
        raise ValueError(f"Unknown setting(s): {', '.join(unknown)}")
    v = values.get("aliases", [])
    if not isinstance(v, list) or not all(isinstance(x, str) and x.count("=") == 1 and all(p.strip() for p in x.split("=")) for x in v):
        raise ValueError("'aliases' must be a list of 'variant=canonical' texts")
    return values


def alias_map(aliases: list[str]) -> dict[str, str]:
    return {a.strip(): b.strip() for a, b in (x.split("=") for x in aliases)}
