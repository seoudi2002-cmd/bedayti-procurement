"""Upload → parse → store facts → analyze. Original files are stored untouched; facts keep their source reference."""
import hashlib
from decimal import Decimal
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.cleaning.normalizers import normalize_text
from app.core.entities import EntityResolver
from app.core.settings_store import effective_thresholds, get_setting
from app.models.analysis import AnalysisDataset, AnalysisFact
from app.modules.custody_analysis import layouts
from app.modules.custody_analysis.engine import F, analyze, name_key

MODULE_ID = "custody_analysis"


class DuplicateDataset(Exception):
    def __init__(self, dataset_id: int):
        super().__init__(f"This exact file was already uploaded (dataset {dataset_id})")
        self.dataset_id = dataset_id


def _jsonable(o):
    if isinstance(o, Decimal):
        return float(o)
    if isinstance(o, tuple):
        return list(o)
    raise TypeError(type(o))


def _suggest_groups(categories: list[str], labels: dict[str, str]) -> list[dict]:
    """Display-grouping SUGGESTIONS only (never applied until approved): categories that share the Arabic label
    the file itself gives them, or that differ only in word order / a trailing 'Exp' / singular-plural."""
    key = name_key
    buckets: dict[str, dict] = {}
    for c in categories:
        for basis, k in (("label_in_file", labels.get(c)), ("similar_name", key(c))):
            if k:
                buckets.setdefault(f"{basis}:{k}", {"basis": basis, "label": labels.get(c) if basis == "label_in_file" else None,
                                                    "members": []})["members"].append(c)
    seen, out = set(), []
    for b in buckets.values():
        m = tuple(sorted(set(b["members"])))
        if len(m) > 1 and m not in seen:
            seen.add(m)
            out.append({"basis": b["basis"], "suggested_label": b["label"], "members": list(m)})
    return out


def ingest(session: Session, content: bytes, filename: str, created_by: str | None, year: int | None = None,
           layout: str | None = None, scope_hint: str | None = None) -> AnalysisDataset:
    digest = hashlib.sha256(content).hexdigest()
    dup = session.scalar(select(AnalysisDataset).where(AnalysisDataset.module_id == MODULE_ID, AnalysisDataset.file_hash == digest))
    if dup:
        raise DuplicateDataset(dup.id)
    kind = layout or layouts.detect_layout(content)
    store_dir = Path(get_settings().upload_dir) / MODULE_ID
    store_dir.mkdir(parents=True, exist_ok=True)
    path = store_dir / f"{digest[:16]}{Path(filename).suffix.lower()}"
    if kind == "advance_register":
        from app.modules.custody_analysis import advances
        ds = advances.store(session, content, filename, created_by, digest, str(path))
        path.write_bytes(content)
        return ds
    parsed = layouts.parse_workbook(content, filename, year, layout, scope_hint)
    path.write_bytes(content)

    mode = get_setting(session, "custody.branch_key", {"mode": "cost_center"}).get("mode", "cost_center")
    resolver = EntityResolver(session, {"branch": "review"})
    resolved: dict[str, int | None] = {}
    unresolved: list[str] = []

    def branch_identity(f: layouts.FactRow) -> tuple[str | None, int | None]:
        if not f.branch_label:
            return None, None
        if f.branch_kind == "head_office":
            return "head_office", None
        if f.branch_kind == "group":
            return "group:" + normalize_text(f.branch_label), None
        norm = normalize_text(f.branch_label)
        if norm not in resolved:
            res = resolver.resolve("branch", f.branch_label)
            resolved[norm] = res.entity_id if res is not None and res.status == "resolved" else None
            if resolved[norm] is None:
                unresolved.append(f.branch_label)
        if resolved[norm]:
            return f"branch:{resolved[norm]}", resolved[norm]
        if mode == "cost_center" and f.cost_center:
            return f"cc:{f.cost_center}", None
        return "name:" + norm, None

    months = [f.month for f in parsed.facts if f.month]
    ds = AnalysisDataset(
        module_id=MODULE_ID, layout=parsed.layout, scope_label=parsed.scope_label, file_name=Path(filename).name,
        file_hash=digest, storage_path=str(path), title=parsed.title, period_year=parsed.year, year_source=parsed.year_source,
        facts_count=len(parsed.facts), created_by=created_by, contains_personal_data=True)
    session.add(ds)
    session.flush()
    for f in parsed.facts:
        key, bid = branch_identity(f)
        session.add(AnalysisFact(
            dataset_id=ds.id, source_ref=f.source_ref, period_year=f.year, period_month=f.month, scope=f.scope,
            branch_key=key, branch_label=f.branch_label, branch_kind=f.branch_kind, branch_id=bid,
            cost_center_code=f.cost_center, category_source=f.category, item_source=f.item, account_no=f.account_no,
            holder_text=f.holder, ref_no=f.ref_no, description_raw=f.description, amount=f.amount, flags=f.flags))
    if unresolved:
        parsed.issues.append(layouts.Issue("branch_not_in_master", "info",
                                           "Branch names not found in the branch master (reported as written in the file)",
                                           len(set(unresolved)), sorted(set(unresolved))[:8]))
    cats = sorted({f.category for f in parsed.facts if f.category})
    ds.summary = {
        "sheets": parsed.sheets, "skipped_sheets": parsed.skipped_sheets, "months": sorted(set(months)),
        "presence": parsed.presence,
        "issues": [{"code": i.code, "severity": i.severity, "message": i.message, "count": i.count, "examples": i.examples}
                   for i in parsed.issues],
        "controls": [{"label": c.label, "month": c.month, "stated": None if c.stated is None else float(c.stated),
                      "computed": float(c.computed), "source_ref": c.source_ref, "note": c.note} for c in parsed.controls],
        "labels": parsed.labels, "suggested_groups": _suggest_groups(cats, parsed.labels),
    }
    session.commit()
    return ds


def delete_dataset(session: Session, dataset_id: int) -> None:
    ds = session.get(AnalysisDataset, dataset_id)
    if ds is not None and ds.layout == "advance_register":
        from app.modules.custody_analysis import advances
        advances.delete(session, dataset_id)
        return
    session.execute(delete(AnalysisFact).where(AnalysisFact.dataset_id == dataset_id))
    session.execute(delete(AnalysisDataset).where(AnalysisDataset.id == dataset_id))
    session.commit()


def load_facts(session: Session, dataset_id: int) -> list[F]:
    rows = session.scalars(select(AnalysisFact).where(AnalysisFact.dataset_id == dataset_id)).all()
    return [F(r.period_year, r.period_month, r.scope, r.branch_key, r.branch_label, r.branch_kind, r.category_source,
              r.item_source, r.holder_text, Decimal(r.amount), r.source_ref, r.ref_no, tuple(r.flags or ())) for r in rows]


def period_id(f: F) -> str:
    return f"{f.year or 0}-{(f.month or 0):02d}"


def apply_filters(facts: list[F], active: dict | None) -> list[F]:
    """Narrow the facts to the selected periods / branches / categories (the analysis is then recomputed on them)."""
    if not active:
        return facts
    periods, branches, cats = set(active.get("periods") or ()), set(active.get("branches") or ()), set(active.get("categories") or ())
    return [f for f in facts if (not periods or (f.month and period_id(f) in periods))
            and (not branches or f.branch_key in branches) and (not cats or f.category in cats)]


def filter_options(facts: list[F], lang: str, year: int | None) -> dict:
    from app.modules.custody_analysis.report import MONTH_NAMES
    periods = sorted({(f.year or 0, f.month) for f in facts if f.month})
    spell: dict[str, dict[str, int]] = {}
    kind: dict[str, str | None] = {}
    for f in facts:
        if f.branch_key:
            name = f.branch_label or f.branch_key
            spell.setdefault(f.branch_key, {})[name] = spell.get(f.branch_key, {}).get(name, 0) + 1
            kind[f.branch_key] = f.branch_kind
    branches = [{"key": k, "label": max(v.items(), key=lambda kv: kv[1])[0], "kind": kind[k]} for k, v in spell.items()]
    branches.sort(key=lambda b: (b["kind"] != "head_office", b["label"].casefold()))
    return {
        "periods": [{"id": f"{y}-{m:02d}", "label": MONTH_NAMES[lang][m - 1] + (f" {y or year}" if (y or year) else "")} for y, m in periods],
        "branches": branches,
        "categories": sorted({f.category for f in facts if f.category}, key=str.casefold)}


def run_analysis(session: Session, dataset: AnalysisDataset, filters: dict | None = None) -> dict:
    th, origin = effective_thresholds(session)
    facts = apply_filters(load_facts(session, dataset.id), filters)
    res = analyze(facts, th, None if filters else dataset.summary.get("presence"), continuous=dataset.layout.startswith("monthly_"))
    res["thresholds"], res["thresholds_origin"] = th, origin
    return res


def holder_rows(session: Session, dataset: AnalysisDataset, filters: dict | None = None) -> list[dict]:
    """Totals per custodian (personal data: only built for admins)."""
    tot: dict[str, dict] = {}
    for f in apply_filters(load_facts(session, dataset.id), filters):
        if not f.holder:
            continue
        key = normalize_text(f.holder)
        r = tot.setdefault(key, {"holder": f.holder, "total": Decimal("0"), "lines": 0})
        r["total"] += f.amount
        r["lines"] += 1
    grand = sum((r["total"] for r in tot.values()), Decimal("0"))
    rows = sorted(tot.values(), key=lambda r: r["total"], reverse=True)
    for r in rows:
        r["share"] = float(r["total"] / grand * 100) if grand else None
    return rows


def build(session: Session, dataset: AnalysisDataset, lang: str, admin: bool, filters: dict | None = None):
    from app.modules.custody_analysis.report import build_report
    filters = {k: v for k, v in (filters or {}).items() if v}
    all_facts = load_facts(session, dataset.id)
    options = filter_options(all_facts, lang, dataset.period_year)
    a = run_analysis(session, dataset, filters)
    taxonomy = get_setting(session, "custody.display_taxonomy", {}) or {}
    rm = build_report(dataset, a, lang, admin, taxonomy, holder_rows(session, dataset, filters) if admin else None,
                      filters=filters, options=options)
    return rm, a
