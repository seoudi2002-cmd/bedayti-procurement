"""Suggest source-header → canonical-field mappings from a module's alias dictionary."""
import hashlib
from difflib import SequenceMatcher

from app.core.cleaning.normalizers import normalize_text
from app.core.modules.spec import ModuleSchema

FUZZY_THRESHOLD = 0.85


def header_signature(headers: list[str]) -> str:
    """Stable fingerprint of a file layout so a saved mapping template can be recognised later."""
    joined = "|".join(sorted(normalize_text(h) for h in headers))
    return hashlib.sha256(joined.encode()).hexdigest()


def suggest_mapping(headers: list[str], schema: ModuleSchema) -> dict[str, dict]:
    """Return {header: {"field": name, "score": 0-1}} for confident matches; each field maps at most once."""
    candidates: list[tuple[float, str, str]] = []
    for header in headers:
        norm = normalize_text(header) or str(header).strip()  # headers like "#" normalise to nothing
        if not norm:
            continue
        for f in schema.fields:
            names = [f.name, f.label, *f.aliases]
            best = 0.0
            for alias in names:
                a = normalize_text(alias) or str(alias).strip()
                if not a:
                    continue
                score = 1.0 if a == norm else SequenceMatcher(None, a, norm).ratio()
                best = max(best, score)
            if best >= FUZZY_THRESHOLD:
                candidates.append((best, header, f.name))
    result: dict[str, dict] = {}
    used_fields: set[str] = set()
    for score, header, fname in sorted(candidates, key=lambda c: -c[0]):
        if header in result or fname in used_fields:
            continue
        result[header] = {"field": fname, "score": round(score, 3)}
        used_fields.add(fname)
    return result


def missing_required(mapped_fields: set[str], schema: ModuleSchema) -> list[str]:
    return [f.name for f in schema.fields if f.required and f.name not in mapped_fields and f.derive is None]
