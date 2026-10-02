"""Identify which module/profile a file (or each sheet of a workbook) belongs to, by header coverage.

Tabular files only today. Word/PDF extractors will plug into core/ingestion/readers.py and then use exactly
the same detection and the same import pipeline.
"""
from app.core.ingestion.readers import read_table
from app.core.mapping.engine import suggest_mapping
from app.core.modules.registry import ModuleRegistry


def analyze_file(registry: ModuleRegistry, filename: str, content: bytes) -> list[dict]:
    first = read_table(filename, content)
    sheets = first.sheet_names or [None]
    out = []
    for sheet in sheets:
        table = first if sheet in (None, first.sheet_name) else read_table(filename, content, sheet=sheet)
        cands = []
        for module in registry.all():
            for code in ["default", *[p.code for p in module.manifest.profiles]]:
                schema = module.schema_for(code)
                mapping = suggest_mapping(table.headers, schema)
                matched = {m["field"] for m in mapping.values()}
                required = [f.name for f in schema.fields if f.required and f.derive is None]
                req_frac = (sum(r in matched for r in required) / len(required)) if required else 0.0
                all_frac = len(matched) / len(schema.fields)
                bonus = 1.0 if schema.sheet and schema.sheet == sheet else 0.0
                score = round(0.6 * req_frac + 0.3 * all_frac + 0.1 * bonus, 3)
                if matched:
                    cands.append({"module_id": module.manifest.id, "profile": code, "score": score,
                                  "matched_fields": sorted(matched),
                                  "missing_required": [r for r in required if r not in matched]})
        cands.sort(key=lambda c: -c["score"])
        out.append({"sheet": table.sheet_name, "rows": len(table.rows), "header_row": table.header_row,
                    "headers": table.headers, "candidates": cands[:3],
                    "recommended": cands[0] if cands and cands[0]["score"] >= 0.6 else None})
    return out
