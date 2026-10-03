"""Who sent / received a shipment — decided only from explicit evidence, never from a city alone.

Evidence, per side (sender: shipper name + 'sent by' + origin; receiver: consignee name + attention + destination):
  * a party label naming a branch ("<prefix> X")      -> that branch (confirmed against the branch register when it knows the name)
  * Head Office: a label containing the Head Office phrase, a configured contact name, or a configured Head Office location
  * both kinds of evidence, or two different branches   -> Unallocated (conflicting evidence)
  * neither                                             -> Unallocated (no branch evidence)
A city is never mapped to a branch. Everything is exact normalised text; nothing is fuzzy-matched."""
from dataclasses import dataclass

from app.core.cleaning.normalizers import normalize_text

HQ_KEY, UNALLOC_KEY = "head_office", "unallocated"


@dataclass(frozen=True)
class Rules:
    locations: frozenset
    labels: tuple
    contacts: frozenset
    prefixes: tuple


def rules_from(settings: dict) -> Rules:
    n = normalize_text
    return Rules(frozenset(n(x) for x in settings.get("head_office_locations", []) if n(x)),
                 tuple(n(x) for x in settings.get("head_office_labels", []) if n(x)),
                 frozenset(n(x) for x in settings.get("head_office_contacts", []) if n(x)),
                 tuple(sorted((n(x) for x in settings.get("branch_label_prefixes", []) if n(x)), key=len, reverse=True)))


def branch_name(value: str | None, rules: Rules) -> str | None:
    """The branch named by a label such as '<prefix> X' (original spelling kept), else None."""
    nv = normalize_text(value)
    for p in rules.prefixes:
        if nv.startswith(p + " ") and nv[len(p):].strip():
            words = " ".join(str(value).split()).split(" ")
            k = len(p.split(" "))
            return " ".join(words[k:]).strip() or None
    return None


def _hq_evidence(value: str | None, rules: Rules) -> bool:
    nv = normalize_text(value)
    return bool(nv) and (nv in rules.contacts or any(lbl in nv for lbl in rules.labels))


def allocate_side(fields: list[str | None], location: str | None, rules: Rules, resolve) -> dict:
    """resolve(name) -> {"key","display","kind","registered"} for a branch name. Returns the party of this side."""
    named = {}
    for f in fields:
        b = branch_name(f, rules)
        if b:
            r = resolve(b)
            named[r["key"]] = r
    hq = any(_hq_evidence(f, rules) for f in fields) or normalize_text(location) in rules.locations
    if named and hq:
        return {"kind": "unallocated", "key": UNALLOC_KEY, "display": None, "reason": "conflicting_evidence", "registered": None}
    if len(named) > 1:
        return {"kind": "unallocated", "key": UNALLOC_KEY, "display": None, "reason": "conflicting_branches", "registered": None}
    if named:
        r = next(iter(named.values()))
        if r["kind"] == "head_office":
            return {"kind": "head_office", "key": HQ_KEY, "display": None, "reason": None, "registered": True}
        if r["kind"] == "unallocated":
            return {"kind": "unallocated", "key": UNALLOC_KEY, "display": None, "reason": "register_unallocated", "registered": True}
        return {"kind": "branch", "key": r["key"], "display": r["display"], "reason": None, "registered": r["registered"]}
    if hq:
        return {"kind": "head_office", "key": HQ_KEY, "display": None, "reason": None, "registered": None}
    return {"kind": "unallocated", "key": UNALLOC_KEY, "display": None, "reason": "no_branch_evidence", "registered": None}
