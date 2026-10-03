"""Overtime analytics over the effective monthly entries. Hours only (no amounts exist in the statement); a listed employee with no entry
for a month is «no entry», never zero; a month with no statement is «not available»."""
import statistics
from collections import defaultdict

from app.core.analysis.opsupport import months_between, period_str, period_tuple


def prev_period(p: str, n: int = 1) -> str:
    y, m = period_tuple(p)
    t = y * 12 + (m - 1) - n
    return period_str(t // 12, t % 12 + 1)


def _pct(a, b):
    return None if not b else (a - b) / b * 100


def _n(v):
    return v or 0.0


def analyze(rows: list[dict], roster: list[dict], th: dict, focus: str | None = None, filters: dict | None = None) -> dict:
    filters = filters or {}
    if filters.get("employees"):
        keep = set(filters["employees"])
        rows = [r for r in rows if r["code"] in keep]
        roster = [r for r in roster if r["code"] in keep]
    if focus:
        rows = [r for r in rows if r["period"] <= focus]
        roster = [r for r in roster if r["period"] <= focus]
    stated = sorted({r["period"] for r in roster})
    if not stated:
        return {"empty": True}
    first, last = stated[0], stated[-1]
    periods = months_between(first, last)
    missing = [p for p in periods if p not in stated]
    for r in rows:
        r["hours"] = _n(r["day_hours"]) + _n(r["night_hours"])
        r["weighted"] = r["weighted_total"] if r["weighted_total"] is not None else (_n(r["day_weighted"]) + _n(r["night_weighted"]) if (r["day_weighted"] is not None or r["night_weighted"] is not None) else None)
    by_period: dict[str, list] = defaultdict(list)
    for r in rows:
        by_period[r["period"]].append(r)
    listed = defaultdict(int)
    for r in roster:
        listed[r["period"]] += 1

    months = []
    for p in periods:
        if p in missing:
            months.append({"period": p, "available": False})
            continue
        rs = by_period.get(p, [])
        m = {"period": p, "available": True, "listed": listed[p], "entries": len(rs), "active": sum(1 for r in rs if r["hours"] > 0 or _n(r["mission_day"]) + _n(r["mission_night"]) > 0),
             "day_hours": sum(_n(r["day_hours"]) for r in rs), "night_hours": sum(_n(r["night_hours"]) for r in rs), "weighted": sum(_n(r["weighted"]) for r in rs), "meals": sum(_n(r["meals"]) for r in rs),
             "mission_day": sum(_n(r["mission_day"]) for r in rs), "mission_night": sum(_n(r["mission_night"]) for r in rs), "equal_pay_days": sum(_n(r["equal_pay_days"]) for r in rs)}
        m["hours"] = m["day_hours"] + m["night_hours"]
        m["night_share"] = m["night_hours"] / m["hours"] * 100 if m["hours"] else None
        m["avg_per_active"] = m["hours"] / m["active"] if m["active"] else None
        months.append(m)
    avail = [m for m in months if m["available"]]
    for i, m in enumerate(avail):
        if i:
            pm = avail[i - 1]
            m["d"], m["dpct"] = m["weighted"] - pm["weighted"], _pct(m["weighted"], pm["weighted"])
            m["gap_before"] = pm["period"] != prev_period(m["period"])
        m["large"] = bool(i and m.get("dpct") is not None and abs(m["dpct"]) >= th["mom_change_pct"] and not m.get("gap_before"))
    cur = avail[-1]

    # ---------------------------------------------------------------- employees (cumulative)
    emp: dict = {}
    for r in rows:
        e = emp.setdefault(r["code"], {"code": r["code"], "name": r["name"], "by_month": {}, "n": 0, "day_hours": 0.0, "night_hours": 0.0, "weighted": 0.0, "meals": 0.0, "missions": 0.0, "hours": 0.0})
        e["by_month"][r["period"]] = r["hours"]
        e["n"] += 1
        e["day_hours"] += _n(r["day_hours"])
        e["night_hours"] += _n(r["night_hours"])
        e["weighted"] += _n(r["weighted"])
        e["meals"] += _n(r["meals"])
        e["missions"] += _n(r["mission_day"]) + _n(r["mission_night"])
        e["hours"] += r["hours"]
    names = {}
    for r in roster:
        names.setdefault(r["code"], r["name"])
    for code, nm in names.items():
        emp.setdefault(code, {"code": code, "name": nm, "by_month": {}, "n": 0, "day_hours": 0.0, "night_hours": 0.0, "weighted": 0.0, "meals": 0.0, "missions": 0.0, "hours": 0.0})["name"] = nm
    listed_months = defaultdict(int)
    for r in roster:
        listed_months[r["code"]] += 1
    erows = []
    total_h = sum(e["hours"] for e in emp.values())
    for e in emp.values():
        e["listed_months"] = listed_months[e["code"]]
        e["avg_month"] = e["hours"] / e["n"] if e["n"] else None
        e["share"] = e["hours"] / total_h * 100 if total_h else None
        e["max_month"] = max(e["by_month"].items(), key=lambda kv: kv[1]) if e["by_month"] else None
        e["cur"] = e["by_month"].get(cur["period"])
        erows.append(e)
    erows.sort(key=lambda e: (-e["hours"], e["code"]))
    cum = 0.0
    for e in erows:
        cum += e["share"] or 0
        e["cum"] = cum
    topn = int(th["concentration_top_n"])
    conc = sum(e["share"] or 0 for e in erows[:topn])

    # ---------------------------------------------------------------- high months
    high = []
    for e in erows:
        if e["n"] >= th["min_entry_months"] and e["avg_month"]:
            for p, h in e["by_month"].items():
                if h >= th["high_month_factor"] * e["avg_month"] and h > 0:
                    high.append({"code": e["code"], "name": e["name"], "period": p, "hours": h, "avg": e["avg_month"], "factor": h / e["avg_month"]})
    high.sort(key=lambda x: -x["factor"])

    # ---------------------------------------------------------------- by year (annual cumulative)
    years: dict = {}
    for m in avail:
        y = m["period"][:4]
        d = years.setdefault(y, {"year": y, "months": 0, "day_hours": 0.0, "night_hours": 0.0, "weighted": 0.0, "meals": 0.0, "missions": 0.0})
        d["months"] += 1
        d["day_hours"] += m["day_hours"]
        d["night_hours"] += m["night_hours"]
        d["weighted"] += m["weighted"]
        d["meals"] += m["meals"]
        d["missions"] += m["mission_day"] + m["mission_night"]
    for d in years.values():
        d["hours"] = d["day_hours"] + d["night_hours"]
        d["avg_month"] = d["hours"] / d["months"] if d["months"] else None
    peak = max(avail, key=lambda m: m["hours"])
    low = min(avail, key=lambda m: m["hours"])
    cy = [m for m in avail if m["period"][:4] == cur["period"][:4]]
    totals = {"last": cur["period"], "first": first, "months_available": len(avail), "missing": missing, "employees": len(emp), "cur": cur,
              "ytd_hours": sum(m["hours"] for m in cy), "ytd_weighted": sum(m["weighted"] for m in cy), "ytd_months": len(cy), "ytd_year": cur["period"][:4],
              "all_hours": sum(m["hours"] for m in avail), "all_weighted": sum(m["weighted"] for m in avail), "peak": peak["period"], "peak_hours": peak["hours"], "low": low["period"], "low_hours": low["hours"],
              "concentration_pct": conc, "concentration_n": topn, "night_share": cur["night_share"], "empty_rows": sum(1 for m in avail for _ in range(m["listed"] - m["entries"])),
              "avg_month_hours": statistics.mean(m["hours"] for m in avail)}
    return {"empty": False, "filtered": bool(filters), "periods": periods, "months": months, "avail": avail, "employees": erows, "high": high, "years": [years[y] for y in sorted(years)], "totals": totals, "thresholds": th}
