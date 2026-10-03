"""Shared plumbing for the time-varying operating modules (rent, vehicles, overtime).

Rule for all of them: a value that changes over time is history, never a replaced number. Each uploaded file is one *version*
(an AnalysisDataset); its values are stored as append-only OpRecord rows tied to it. The *effective* value of any (entity, period,
field) is the one from the most recently uploaded file that states it (a field a newer file does not state keeps the older value);
every difference between versions is kept and can be listed. Nothing is ever deleted from here."""
import hashlib
import re
from collections import defaultdict
from datetime import date
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.analysis import AnalysisError
from app.models import AnalysisDataset, OpRecord

TOL = 0.005


def store_file(module_id: str, content: bytes, filename: str) -> tuple[str, str]:
    digest = hashlib.sha256(content).hexdigest()
    d = Path(get_settings().upload_dir) / module_id
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{digest[:16]}{Path(filename).suffix.lower()}"
    path.write_bytes(content)
    return digest, str(path)


def check_duplicate(session: Session, module_id: str, digest: str) -> None:
    dup = session.scalar(select(AnalysisDataset).where(AnalysisDataset.module_id == module_id, AnalysisDataset.file_hash == digest))
    if dup:
        raise AnalysisError(409, {"message": f"This exact file was already uploaded (version {dup.id}); nothing was added", "dataset_id": dup.id})


def issues_json(items) -> list[dict]:
    return [{"code": i.code, "severity": i.severity, "message": i.message, "count": i.count, "examples": i.examples} for i in items]


class Issues:
    """Collects observations about a file (never fixes anything)."""

    def __init__(self):
        self.items: list = []

    def add(self, code: str, severity: str, message: str, example=None):
        from app.modules.custody_analysis.layouts import Issue
        for i in self.items:
            if i.code == code:
                i.count += 1
                if example is not None and len(i.examples) < 8 and str(example) not in i.examples:
                    i.examples.append(str(example))
                return
        self.items.append(Issue(code, severity, message, 1, [str(example)] if example is not None else []))

    def json(self) -> list[dict]:
        return issues_json(self.items)


def month_bounds(periods: list[str]) -> tuple[date | None, date | None]:
    if not periods:
        return None, None
    lo, hi = min(periods), max(periods)
    return date(int(lo[:4]), int(lo[5:]), 1), date(int(hi[:4]), int(hi[5:]), 1)


def create_dataset(session: Session, module_id: str, layout: str, scope: str, filename: str, digest: str, path: str, user: str | None, summary: dict,
                   periods: list[str], personal: bool, title: str | None = None, year: int | None = None, year_source: str | None = None) -> AnalysisDataset:
    lo, hi = month_bounds(periods)
    ds = AnalysisDataset(module_id=module_id, layout=layout, scope_label=scope, file_name=filename.rsplit("/", 1)[-1], file_hash=digest, storage_path=path, title=title,
                         period_year=year, year_source=year_source, period_from=lo, period_to=hi, facts_count=0, summary=summary, created_by=user,
                         contains_personal_data=personal, role=layout, status="ready")
    session.add(ds)
    session.flush()
    return ds


def add_records(session: Session, ds: AnalysisDataset, records: list[dict]) -> None:
    for r in records:
        session.add(OpRecord(dataset_id=ds.id, module_id=ds.module_id, kind=r["kind"], entity_key=r["key"], entity_label=r.get("label"), period=r.get("period"),
                             source_ref=r.get("ref"), values=r.get("values") or {}, personal=r.get("personal") or None, flags=r.get("flags") or []))
    ds.facts_count = len(records)
    session.commit()


def datasets(session: Session, module_id: str) -> list[AnalysisDataset]:
    return list(session.scalars(select(AnalysisDataset).where(AnalysisDataset.module_id == module_id).order_by(AnalysisDataset.id)))


def load_records(session: Session, module_id: str, kinds: tuple | None = None) -> list[dict]:
    q = select(OpRecord).where(OpRecord.module_id == module_id).order_by(OpRecord.dataset_id, OpRecord.id)
    if kinds:
        q = q.where(OpRecord.kind.in_(kinds))
    return [{"id": r.id, "dataset_id": r.dataset_id, "kind": r.kind, "key": r.entity_key, "label": r.entity_label, "period": r.period, "ref": r.source_ref,
             "values": r.values or {}, "personal": r.personal or {}, "flags": r.flags or []} for r in session.scalars(q)]


def same(a, b) -> bool:
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool) and not isinstance(b, bool):
        return abs(a - b) <= TOL
    return a == b


def resolve(records: list[dict], ignore: tuple = ()) -> dict:
    """Effective rows + the change log. records must be ordered oldest version first (load_records orders them).
    current[(kind, key, period)] = {"values", "personal", "label", "flags", "datasets": [ids], "versions": n, "last_dataset": id}.
    changes: one entry per field whose stated value differs between two consecutive versions that both state it."""
    cur: dict[tuple, dict] = {}
    seq: dict[tuple, dict[str, list]] = defaultdict(lambda: defaultdict(list))    # (kind,key,period) -> field -> [(dataset, value)]
    for r in records:
        k = (r["kind"], r["key"], r["period"])
        c = cur.setdefault(k, {"values": {}, "personal": {}, "label": r["label"], "flags": [], "datasets": [], "versions": 0, "last_dataset": None})
        if r["dataset_id"] not in c["datasets"]:
            c["datasets"].append(r["dataset_id"])
            c["versions"] += 1
        c["last_dataset"] = r["dataset_id"]
        if r["label"]:
            c["label"] = r["label"]
        for f, v in r["values"].items():
            if v is not None:
                c["values"][f] = v
                if f not in ignore:
                    seq[k][f].append((r["dataset_id"], v))
        for f, v in r["personal"].items():
            if v is not None:
                c["personal"][f] = v
        for fl in r["flags"]:
            if fl not in c["flags"]:
                c["flags"].append(fl)
    changes = []
    for k, fields in seq.items():
        for f, steps in fields.items():
            for (d0, v0), (d1, v1) in zip(steps, steps[1:]):
                if d0 != d1 and not same(v0, v1):
                    changes.append({"kind": k[0], "key": k[1], "label": cur[k]["label"], "period": k[2], "field": f, "old": v0, "new": v1, "from_dataset": d0, "to_dataset": d1})
    return {"current": cur, "changes": changes}


def versions_table(session: Session, module_id: str, records: list[dict], changes: list[dict]) -> list[dict]:
    """One row per uploaded file (oldest first): what it holds, what it added relative to the previous file of the same layout and what it changed."""
    dss = datasets(session, module_id)
    per: dict[int, set] = defaultdict(set)
    for r in records:
        per[r["dataset_id"]].add((r["kind"], r["key"], r["period"]))
    prev_by_layout: dict[str, int] = {}
    out = []
    for d in dss:
        prev = prev_by_layout.get(d.layout)
        keys = per.get(d.id, set())
        pk = per.get(prev, set()) if prev else set()
        out.append({"id": d.id, "file": d.file_name, "layout": d.layout, "uploaded_at": d.created_at.strftime("%Y-%m-%d %H:%M") if d.created_at else "",
                    "from": d.period_from.strftime("%Y-%m") if d.period_from else None, "to": d.period_to.strftime("%Y-%m") if d.period_to else None,
                    "records": len(keys), "added": len(keys - pk) if prev else None, "dropped": len(pk - keys) if prev else None,
                    "changed": sum(1 for c in changes if c["to_dataset"] == d.id), "previous": prev})
        prev_by_layout[d.layout] = d.id
    return out


# ------------------------------------------------------------------------------------------------ small shared parsing helpers
_FOLD = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي", "ة": "ه", "ؤ": "و", "ئ": "ي", "ـ": ""})


def fold(s) -> str:
    """Arabic comparison form (hamza/ya/ta-marbuta folded, tatweel dropped, spaces collapsed). For comparing only; display keeps the file's text."""
    return " ".join(str(s if s is not None else "").translate(_FOLD).split()).lower()


MONTH_TOKENS = {
    "يناير": 1, "فبراير": 2, "مارس": 3, "ابريل": 4, "ابرايل": 4, "مايو": 5, "يونيو": 6, "يونيه": 6, "يونيو.": 6, "يونية": 6, "يوليو": 7, "يوليه": 7, "يوليو.": 7,
    "اغسطس": 8, "سبتمبر": 9, "سبتمير": 9, "اكتوبر": 10, "نوفمبر": 11, "ديسمبر": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}
_YEAR = re.compile(r"(?<!\d)(20\d{2})(?!\d)")


def month_in_text(text) -> tuple[int | None, int | None]:
    """(month, year) found in a header/title text such as 'يناير 2025' or 'فبراير2025' (year None when the text has none)."""
    t = fold(text)
    m = y = None
    for tok, n in MONTH_TOKENS.items():
        if tok in t:
            m = n
            break
    ym = _YEAR.search(t)
    if ym:
        y = int(ym.group(1))
    return m, y


def num(v):
    """A number as stated, else None (text such as '_____' or '-' is not a number)."""
    if isinstance(v, bool) or v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = v.strip().replace(",", "")
        if re.fullmatch(r"-?\d+(\.\d+)?", s):
            return float(s)
    return None


def period_str(y: int, m: int) -> str:
    return f"{y}-{m:02d}"


def period_tuple(p: str) -> tuple[int, int]:
    return int(p[:4]), int(p[5:7])


def months_between(lo: str, hi: str) -> list[str]:
    y, m = period_tuple(lo)
    out = []
    while period_str(y, m) <= hi:
        out.append(period_str(y, m))
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out
