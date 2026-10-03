"""Deterministic analysis of canonical custody facts. Pure functions: no database, no randomness, no AI.

Every number in a report comes from here and can be traced to fact rows (source_ref). Thresholds are inputs
(system setting `custody.thresholds`), never constants. A dimension the facts do not carry produces no
analysis for it and is listed in `unsupported` instead.
"""
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from statistics import median, quantiles

ZERO = Decimal("0")


def name_key(c: str) -> str:
    """Spelling-insensitive key used only to DETECT possible naming variants of one category (never to merge)."""
    import re

    from app.core.cleaning.normalizers import normalize_text
    toks = [t.rstrip("s") for t in re.split(r"[\s&]+", normalize_text(c).replace(".", "")) if t and t not in ("exp", "and")]
    return " ".join(sorted(toks))


def inconsistent_periods(by_period: dict, min_names: int = 10) -> set:
    """Periods whose branch names barely overlap with every other period's (e.g. one sheet written in another
    language): branch-level period-to-period comparisons involving them would be artefacts, so they are excluded."""
    bad = set()
    for p, names in by_period.items():
        if len(names) < min_names:
            continue
        best = max((len(names & q) / min(len(names), len(q)) for k, q in by_period.items() if k != p and len(q) >= min_names), default=1.0)
        if best < 0.5:
            bad.add(p)
    return bad


@dataclass
class F:  # one fact (read-only view)
    year: int | None
    month: int | None
    scope: str
    branch_key: str | None
    branch_label: str | None
    branch_kind: str | None
    category: str | None
    item: str | None
    holder: str | None
    amount: Decimal
    source_ref: str
    ref_no: str | None = None
    flags: tuple = ()


def pkey(f: F) -> tuple[int, int]:
    return (f.year or 0, f.month or 0)


def _pct(part: Decimal, whole: Decimal) -> float | None:
    return float(part / whole * 100) if whole else None


def _chg(prev: Decimal, cur: Decimal) -> tuple[Decimal, float | None]:
    return cur - prev, (float((cur - prev) / prev * 100) if prev else None)


def _sum(it) -> Decimal:
    return sum(it, ZERO)


def analyze(facts: list[F], th: dict, presence: list[dict] | None = None, continuous: bool = False) -> dict:
    presence = presence or []
    out: dict = {"unsupported": [], "notes": []}
    n = len(facts)
    total = _sum(f.amount for f in facts)
    dated = [f for f in facts if f.month]
    cap = {
        "month": bool(dated), "year": any(f.year for f in dated),
        "branch": any(f.branch_key for f in facts), "category": any(f.category for f in facts),
        "item": any(f.item for f in facts), "holder": any(f.holder for f in facts),
        "scope_split": len({f.scope for f in facts if f.scope != "unspecified"}) > 1,
    }
    out["capabilities"] = cap
    out["total"] = total
    out["n_facts"] = n
    undated = [f for f in facts if not f.month]
    if undated:
        out["notes"].append({"code": "facts_without_month", "count": len(undated),
                             "amount": _sum(f.amount for f in undated)})

    # ---- periods ---------------------------------------------------------------------------------
    pm: dict[tuple, Decimal] = defaultdict(lambda: ZERO)
    for f in dated:
        pm[pkey(f)] += f.amount
    periods = sorted(pm)
    out["periods"] = []
    prev = None
    for k in periods:
        row = {"key": k, "total": pm[k], "mom_abs": None, "mom_pct": None}
        if prev is not None:
            row["mom_abs"], row["mom_pct"] = _chg(pm[prev], pm[k])
        out["periods"].append(row)
        prev = k
    out["n_periods"] = len(periods)
    if periods:
        vals = [pm[k] for k in periods]
        out["period_stats"] = {
            "avg": _sum(vals) / len(vals), "max_key": max(periods, key=lambda k: pm[k]), "min_key": min(periods, key=lambda k: pm[k]),
            "max": max(vals), "min": min(vals), "first": periods[0], "last": periods[-1],
            "indicative": len(periods) < th["min_months_for_trend"]}
    else:
        out["unsupported"].append("month")

    # ---- categories ------------------------------------------------------------------------------
    cat_tot: dict[str, Decimal] = defaultdict(lambda: ZERO)
    cat_pm: dict[str, dict] = defaultdict(lambda: defaultdict(lambda: ZERO))
    cat_n: dict[str, int] = defaultdict(int)
    for f in facts:
        if f.category:
            cat_tot[f.category] += f.amount
            cat_n[f.category] += 1
            if f.month:
                cat_pm[f.category][pkey(f)] += f.amount
    cats = sorted(cat_tot, key=lambda c: cat_tot[c], reverse=True)
    cum = ZERO
    out["by_category"] = []
    for i, c in enumerate(cats, 1):
        cum += cat_tot[c]
        out["by_category"].append({"name": c, "total": cat_tot[c], "share": _pct(cat_tot[c], total), "rank": i,
                                   "cum_share": _pct(cum, total), "n_lines": cat_n[c], "by_month": dict(cat_pm[c])})
    if not cats:
        out["unsupported"].append("category")
    items: dict[tuple, Decimal] = defaultdict(lambda: ZERO)
    for f in facts:
        if f.item and f.category:
            items[(f.category, f.item)] += f.amount
    out["by_item"] = [{"category": c, "item": i, "total": v, "share": _pct(v, total)}
                      for (c, i), v in sorted(items.items(), key=lambda kv: kv[1], reverse=True)]

    # ---- scope: head office vs branches -----------------------------------------------------------
    if cap["scope_split"]:
        sc_tot = {s: _sum(f.amount for f in facts if f.scope == s) for s in ("head_office", "branch")}
        sc_pm: dict[str, dict] = {s: defaultdict(lambda: ZERO) for s in sc_tot}
        sc_cat: dict[str, dict] = {s: defaultdict(lambda: ZERO) for s in sc_tot}
        for f in facts:
            if f.scope in sc_tot:
                if f.month:
                    sc_pm[f.scope][pkey(f)] += f.amount
                if f.category:
                    sc_cat[f.scope][f.category] += f.amount
        base = sc_tot["head_office"] + sc_tot["branch"]
        out["by_scope"] = {s: {"total": sc_tot[s], "share": _pct(sc_tot[s], base), "by_month": dict(sc_pm[s]),
                               "by_category": dict(sc_cat[s])} for s in sc_tot}
        unspec = _sum(f.amount for f in facts if f.scope == "unspecified")
        if unspec:
            out["notes"].append({"code": "scope_unspecified", "amount": unspec})
    else:
        out["by_scope"] = None
        out["unsupported"].append("head_office_vs_branches")

    # ---- branches ---------------------------------------------------------------------------------
    if cap["branch"]:
        b_tot: dict[str, Decimal] = defaultdict(lambda: ZERO)
        b_meta: dict[str, dict] = {}
        b_pm: dict[str, dict] = defaultdict(lambda: defaultdict(lambda: ZERO))
        b_cat: dict[str, dict] = defaultdict(lambda: defaultdict(lambda: ZERO))
        b_labels: dict[str, dict] = defaultdict(lambda: defaultdict(int))
        for f in facts:
            if not f.branch_key:
                continue
            b_tot[f.branch_key] += f.amount
            b_meta.setdefault(f.branch_key, {"kind": f.branch_kind})
            b_labels[f.branch_key][f.branch_label or f.branch_key] += 1
            if f.month:
                b_pm[f.branch_key][pkey(f)] += f.amount
            if f.category:
                b_cat[f.branch_key][f.category] += f.amount

        def label(k):
            return max(b_labels[k].items(), key=lambda kv: kv[1])[0]

        def rows(kind):
            ks = sorted((k for k in b_tot if b_meta[k]["kind"] == kind), key=lambda k: b_tot[k], reverse=True)
            sub_total = _sum(b_tot[k] for k in ks)
            cumulative = ZERO
            res = []
            for i, k in enumerate(ks, 1):
                cumulative += b_tot[k]
                res.append({"key": k, "name": label(k), "kind": kind, "total": b_tot[k], "rank": i,
                            "share_of_group": _pct(b_tot[k], sub_total), "share_of_all": _pct(b_tot[k], total),
                            "cum_share": _pct(cumulative, sub_total), "months_active": len(b_pm[k]),
                            "by_month": dict(b_pm[k]), "by_category": dict(b_cat[k]),
                            "spellings": sorted(b_labels[k]) if len(b_labels[k]) > 1 else []})
            return res
        out["by_branch"] = rows("branch")
        out["by_group"] = rows("group")
        out["head_office"] = (rows("head_office") or [None])[0]
        tops = [r["total"] for r in out["by_branch"]]
        if tops:
            s = sorted(tops)
            out["branch_stats"] = {
                "count": len(s), "mean": _sum(s) / len(s), "median": Decimal(str(median(s))), "max": s[-1], "min": s[0],
                "p90": Decimal(str(quantiles([float(x) for x in s], n=10, method="inclusive")[-1])) if len(s) >= 3 else None,
                "top5_share": _pct(_sum(s[-5:]), _sum(s)), "top10_share": _pct(_sum(s[-10:]), _sum(s))}
        # branch x category matrix (top-N each)
        topn = int(th["top_n"])
        mc = cats[:topn]
        out["branch_category_matrix"] = {
            "categories": mc, "rows": [{"name": r["name"], "kind": r["kind"], "cells": [r["by_category"].get(c) for c in mc],
                                        "total": r["total"]} for r in out["by_branch"][:topn]]}
        if presence:
            out["presence"] = _presence(presence, periods)
    else:
        out["by_branch"] = out["by_group"] = []
        out["head_office"] = None
        out["unsupported"] += ["branch", "branch_comparison", "top_branches", "branch_by_category"]

    bp: dict[tuple, set] = defaultdict(set)
    for f in facts:
        if f.branch_key and f.branch_kind == "branch" and f.month:
            bp[pkey(f)].add(f.branch_key)
    out["branch_name_inconsistent_periods"] = sorted(inconsistent_periods(bp))
    buckets: dict[str, set] = defaultdict(set)
    for c in cat_tot:
        buckets[name_key(c)].add(c)
    out["category_variants"] = [sorted(v) for v in buckets.values() if len(v) > 1]
    out["variance"] = _variance(periods, cat_pm, out.get("by_branch", []), out.get("by_scope"), pm)
    out["outliers"] = _outliers(facts, th, periods, pm, cat_tot, cat_pm, out.get("by_branch", []), out.get("by_scope"),
                                continuous, presence, set(out["branch_name_inconsistent_periods"]),
                                {c for v in out["category_variants"] for c in v})
    out["kpis"] = _kpis(out, cap)
    return out


def _presence(presence: list[dict], periods) -> dict:
    by_m: dict[int, dict] = defaultdict(lambda: {"rows": 0, "zero": 0})
    for r in presence:
        if r.get("kind") == "head_office":
            continue
        m = r.get("month")
        by_m[m]["rows"] += 1
        if not Decimal(r["total"] or "0"):
            by_m[m]["zero"] += 1
    return {"by_month": {m: v for m, v in sorted(by_m.items(), key=lambda kv: kv[0] or 0)}}


def _variance(periods, cat_pm, branches, scope, pm) -> dict | None:
    if len(periods) < 2:
        return None
    a, b = periods[-2], periods[-1]
    res = {"from": a, "to": b, "total": {"prev": pm[a], "cur": pm[b], "abs": pm[b] - pm[a], "pct": _chg(pm[a], pm[b])[1]}}
    cat = []
    for c, m in cat_pm.items():
        d, pct = _chg(m.get(a, ZERO), m.get(b, ZERO))
        cat.append({"name": c, "prev": m.get(a, ZERO), "cur": m.get(b, ZERO), "abs": d, "pct": pct})
    res["by_category"] = sorted(cat, key=lambda r: abs(r["abs"]), reverse=True)
    br = []
    for r in branches:
        m = r["by_month"]
        d, pct = _chg(m.get(a, ZERO), m.get(b, ZERO))
        br.append({"name": r["name"], "prev": m.get(a, ZERO), "cur": m.get(b, ZERO), "abs": d, "pct": pct})
    res["by_branch"] = sorted(br, key=lambda r: abs(r["abs"]), reverse=True)
    if scope:
        res["by_scope"] = {s: {"prev": v["by_month"].get(a, ZERO), "cur": v["by_month"].get(b, ZERO),
                               "abs": v["by_month"].get(b, ZERO) - v["by_month"].get(a, ZERO)} for s, v in scope.items()}
    return res


def _outliers(facts, th, periods, pm, cat_tot, cat_pm, branches, scope, continuous, presence, bad_periods=frozenset(),
              variant_cats=frozenset()) -> list[dict]:
    out: list[dict] = []
    pct_t, abs_t = Decimal(str(th["mom_pct"])), Decimal(str(th["mom_abs"]))

    def mom(subject_type: str, subject: str, series: dict, skip=frozenset()):
        for a, b in zip(periods, periods[1:]):
            if a in skip or b in skip:
                continue
            prev, cur = series.get(a, ZERO), series.get(b, ZERO)
            d = cur - prev
            if abs(d) < abs_t:
                continue
            if prev:
                pct = d / prev * 100
                if abs(pct) < pct_t:
                    continue
                out.append({"rule": "mom_change", "severity": "warning", "subject_type": subject_type, "subject": subject,
                            "period": b, "value": cur, "baseline": prev, "change_abs": d, "change_pct": float(pct)})
            elif cur >= Decimal(str(th["dormant_new_min_amount"])):
                out.append({"rule": "new_in_period", "severity": "info", "subject_type": subject_type, "subject": subject,
                            "period": b, "value": cur, "baseline": prev, "change_abs": d, "change_pct": None})
    mom("total", "*", pm)
    for c, m in cat_pm.items():
        if c not in variant_cats:  # a category written differently in different months cannot be compared month to month
            mom("category", c, m)
    for r in branches:
        mom("branch", r["name"], r["by_month"], bad_periods)
    if scope:
        for s, v in scope.items():
            mom("scope", s, v["by_month"])

    # month versus the average of the other months
    if len(periods) >= 3:
        for k in periods:
            others = [pm[x] for x in periods if x != k]
            avg = _sum(others) / len(others)
            if avg and abs((pm[k] - avg) / avg * 100) >= Decimal(str(th["month_vs_avg_pct"])):
                out.append({"rule": "month_vs_average", "severity": "info", "subject_type": "total", "subject": "*", "period": k,
                            "value": pm[k], "baseline": avg, "change_abs": pm[k] - avg, "change_pct": float((pm[k] - avg) / avg * 100),
                            "indicative": len(periods) < th["min_months_for_trend"]})

    # branch totals far above the others (Tukey fence)
    tots = sorted(r["total"] for r in branches if r["total"] > 0)
    if len(tots) >= th["min_branches_for_iqr"]:
        q1, _, q3 = quantiles([float(x) for x in tots], n=4, method="inclusive")
        fence = q3 + float(th["iqr_k"]) * (q3 - q1)
        for r in branches:
            if float(r["total"]) > fence:
                out.append({"rule": "branch_above_fence", "severity": "warning", "subject_type": "branch", "subject": r["name"],
                            "period": None, "value": r["total"], "baseline": Decimal(str(round(fence, 2))), "change_abs": None,
                            "change_pct": None})

    # one line carrying a large share of its category
    share_t, min_line = Decimal(str(th["line_share_of_category_pct"])), Decimal(str(th["min_line_amount"]))
    for f in facts:
        tot = cat_tot.get(f.category or "")
        if tot and f.amount >= min_line and f.amount / tot * 100 >= share_t:
            out.append({"rule": "dominant_line", "severity": "info", "subject_type": "category", "subject": f.category,
                        "period": pkey(f) if f.month else None, "value": f.amount, "baseline": tot, "change_abs": None,
                        "change_pct": float(f.amount / tot * 100), "refs": [f.source_ref]})

    # repeated identical (rounded) amounts in one category
    rep: dict[tuple, list] = defaultdict(list)
    for f in facts:
        if f.category and f.amount >= Decimal(str(th["repeat_amount_min_value"])):
            rep[(f.category, f.amount)].append(f.source_ref)
    for (c, amt), refs in rep.items():
        if len(refs) >= th["repeat_amount_min_count"]:
            out.append({"rule": "repeated_amount", "severity": "info", "subject_type": "category", "subject": c, "period": None,
                        "value": amt, "baseline": None, "change_abs": None, "change_pct": None, "count": len(refs), "refs": refs[:6]})

    # flagged source lines
    for f in facts:
        if "negative_amount" in f.flags or "reclass_entry" in f.flags:
            out.append({"rule": "negative_amount" if "negative_amount" in f.flags else "reclass_entry", "severity": "warning",
                        "subject_type": "category", "subject": f.category, "period": pkey(f) if f.month else None, "value": f.amount,
                        "baseline": None, "change_abs": None, "change_pct": None, "refs": [f.source_ref]})

    # a branch that starts or stops spending (only meaningful for continuously reported monthly files)
    ok_periods = [k for k in periods if k not in bad_periods]
    if continuous and len(ok_periods) >= 3:
        periods_ = periods
        periods = ok_periods
        mn = Decimal(str(th["dormant_new_min_amount"]))
        starts, stops = [], []
        for r in branches:
            m = r["by_month"]
            active = [k for k in periods if m.get(k, ZERO) != 0]
            if not active:
                continue
            if active[0] != periods[0] and m[active[0]] >= mn:
                starts.append((r["name"], m[active[0]], active[0]))
            if active[-1] != periods[-1] and _sum(m.values()) >= mn:
                stops.append((r["name"], m[active[-1]], active[-1]))
        for rule, lst in (("branches_start_spending", starts), ("branches_stop_spending", stops)):
            if lst:
                lst.sort(key=lambda x: x[1], reverse=True)
                out.append({"rule": rule, "severity": "info", "subject_type": "branch", "subject": ", ".join(x[0] for x in lst[:5]),
                            "period": None, "value": _sum(x[1] for x in lst), "baseline": None, "change_abs": None,
                            "change_pct": None, "count": len(lst)})
        periods = periods_
    sev = {"critical": 0, "warning": 1, "info": 2}
    out.sort(key=lambda o: (sev[o["severity"]], -(abs(o["change_abs"]) if o.get("change_abs") is not None else abs(o["value"]))))
    return out


def _kpis(a: dict, cap: dict) -> list[dict]:
    k = [{"id": "total", "value": a["total"]}, {"id": "n_facts", "value": a["n_facts"]}]
    if a.get("period_stats"):
        ps = a["period_stats"]
        k += [{"id": "avg_month", "value": ps["avg"]}, {"id": "peak_month", "value": ps["max"], "period": ps["max_key"]},
              {"id": "low_month", "value": ps["min"], "period": ps["min_key"]}]
    if a.get("variance"):
        v = a["variance"]
        k.append({"id": "last_vs_prev", "value": v["total"]["abs"], "pct": v["total"]["pct"], "from": v["from"], "to": v["to"]})
    if a["by_category"]:
        c = a["by_category"][0]
        k.append({"id": "top_category", "name": c["name"], "value": c["total"], "pct": c["share"]})
    if a.get("by_scope"):
        s = a["by_scope"]
        k.append({"id": "head_office_share", "value": s["head_office"]["total"], "pct": s["head_office"]["share"]})
    if a.get("by_branch"):
        b = a["by_branch"][0]
        k.append({"id": "top_branch", "name": b["name"], "value": b["total"], "pct": b["share_of_all"]})
        k.append({"id": "n_branches", "value": len(a["by_branch"])})
    k.append({"id": "n_outliers", "value": len(a["outliers"])})
    return k
