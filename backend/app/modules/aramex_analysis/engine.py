"""Aramex analysis: per-branch sent / received shipments and cost, month-on-month, allocation quality, reconciliation of the
invoice PDF with its Excel, and supporting analyses. Pure functions over plain dicts; money is Decimal and is never apportioned:
a shipment's whole cost is attributed to its sender and, separately, to its receiver."""
import math
import statistics
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from app.core.cleaning.normalizers import normalize_text

ZERO = Decimal(0)


def _pct(a, b):
    return float(Decimal(a) / Decimal(b) * 100) if b else None


def month_of(r) -> tuple[int, int] | None:
    d = r.get("pickup_on")
    return (d.year, d.month) if d else None


# ------------------------------------------------------------------------------------------------ merge
def merge(pdf_rows: list[dict], xlsx_rows: list[dict]) -> tuple[list[dict], list[dict]]:
    """Join the two sources by AWB. Shipments present in only one source are returned as exceptions and are NOT analysed
    (without the PDF there is no date, without the Excel no parties): the control rows then show the difference."""
    xi = {r["awb"]: r for r in xlsx_rows}
    out, exc = [], []
    for p in pdf_rows:
        x = xi.pop(p["awb"], None)
        if x is None:
            exc.append({"code": "awb_only_in_pdf", "awb": p["awb"], "net": p["net"]})
            continue
        out.append({"awb": p["awb"], "invoice_id": p["invoice_id"], "bill_doc": p.get("bill_doc"), "seq": p["seq"], "pickup_on": p["pickup_on"],
                    "product": p["product"], "pcs": p["pcs"], "weight": p["weight"], "actual_weight": x.get("actual_weight"),
                    "base": p["base"], "other": p["other"], "net": p["net"], "tax": x["tax"], "gross": p["net"] + x["tax"],
                    "origin": x["origin"], "destination": x["destination"], "shipper_name": x["shipper_name"], "sent_by": x["sent_by"],
                    "consignee_name": x["consignee_name"], "attention": x["attention"]})
    for awb, x in xi.items():
        exc.append({"code": "awb_only_in_xlsx", "awb": awb, "net": x["base"] + x["other"]})
    return out, exc


# ------------------------------------------------------------------------------------------------ parties
def _party_name(p: dict) -> str | None:
    return p["display"]


def party_table(rows: list[dict]) -> list[dict]:
    t: dict[str, dict] = {}

    def get(p):
        k = p["key"]
        if k not in t:
            t[k] = {"key": k, "kind": p["kind"], "name": _party_name(p), "registered": p.get("registered"), "sent_n": 0, "sent_cost": ZERO,
                    "sent_gross": ZERO, "recv_n": 0, "recv_cost": ZERO, "recv_gross": ZERO}
        return t[k]
    for r in rows:
        s, c = get(r["sender"]), get(r["receiver"])
        s["sent_n"] += 1
        s["sent_cost"] += r["net"]
        s["sent_gross"] += r["gross"]
        c["recv_n"] += 1
        c["recv_cost"] += r["net"]
        c["recv_gross"] += r["gross"]
    out = list(t.values())
    for p in out:
        p["total_n"] = p["sent_n"] + p["recv_n"]
        p["total_cost"] = p["sent_cost"] + p["recv_cost"]
        p["total_gross"] = p["sent_gross"] + p["recv_gross"]
        p["avg_cost"] = p["total_cost"] / p["total_n"] if p["total_n"] else None
    order = {"branch": 0, "head_office": 1, "unallocated": 2}
    return sorted(out, key=lambda p: (order[p["kind"]], -p["total_cost"], p["name"] or ""))


def _prev_month(m):
    return (m[0] - 1, 12) if m[1] == 1 else (m[0], m[1] - 1)


def mom_table(all_rows: list[dict], month: tuple[int, int], th: dict) -> dict:
    prev = _prev_month(month)
    cur_rows = [r for r in all_rows if month_of(r) == month]
    prev_rows = [r for r in all_rows if month_of(r) == prev]
    res = {"month": month, "prev": prev, "prev_available": bool(prev_rows), "rows": []}
    cur, old = {p["key"]: p for p in party_table(cur_rows)}, {p["key"]: p for p in party_table(prev_rows)}
    for k in list(cur) + [k for k in old if k not in cur]:
        c, o = cur.get(k), old.get(k)
        ref = c or o
        row = {"key": k, "kind": ref["kind"], "name": ref["name"], "cur_n": c["total_n"] if c else 0, "cur_cost": c["total_cost"] if c else ZERO,
               "prev_n": o["total_n"] if o else (0 if prev_rows else None), "prev_cost": o["total_cost"] if o else (ZERO if prev_rows else None)}
        if prev_rows:
            row["d_n"], row["d_cost"] = row["cur_n"] - row["prev_n"], row["cur_cost"] - row["prev_cost"]
            row["d_n_pct"], row["d_cost_pct"] = _pct(row["d_n"], row["prev_n"]), _pct(row["d_cost"], row["prev_cost"])
            row["notable"] = row["d_cost_pct"] is not None and abs(row["d_cost_pct"]) >= th["mom_change_pct"]
        res["rows"].append(row)
    order = {"branch": 0, "head_office": 1, "unallocated": 2}
    res["rows"].sort(key=lambda r: (order[r["kind"]], -r["cur_cost"], r["name"] or ""))
    return res


def party_months(rows: list[dict]) -> dict[str, dict]:
    """party key -> {month: {"n", "cost"}} counting both sides (sent + received)."""
    out: dict[str, dict] = defaultdict(dict)
    for r in rows:
        m = month_of(r)
        if m is None:
            continue
        for side in ("sender", "receiver"):
            k = r[side]["key"]
            cell = out[k].setdefault(m, {"n": 0, "cost": ZERO})
            cell["n"] += 1
            cell["cost"] += r["net"]
    return out


def months_table(rows: list[dict], coverage: tuple[date, date] | None) -> list[dict]:
    by: dict[tuple, dict] = {}
    for r in rows:
        m = month_of(r)
        if m is None:
            continue
        c = by.setdefault(m, {"period": m, "n": 0, "net": ZERO, "gross": ZERO, "kg": ZERO})
        c["n"] += 1
        c["net"] += r["net"]
        c["gross"] += r["gross"]
        c["kg"] += r["weight"] or ZERO
    out = sorted(by.values(), key=lambda c: c["period"])
    prev = None
    for c in out:
        y, mo = c["period"]
        first, last = date(y, mo, 1), date(y + (mo == 12), mo % 12 + 1, 1) - timedelta(days=1)
        c["partial"] = bool(coverage and (first < coverage[0] or last > coverage[1]))   # the uploaded invoices do not span the whole month
        c["avg_net"] = c["net"] / c["n"] if c["n"] else None
        if prev is not None and _prev_month(c["period"]) == prev["period"]:
            c["d_n"], c["d_net"] = c["n"] - prev["n"], c["net"] - prev["net"]
            c["d_n_pct"], c["d_net_pct"] = _pct(c["d_n"], prev["n"]), _pct(c["d_net"], prev["net"])
        prev = c
    return out


# ------------------------------------------------------------------------------------------------ allocation quality
def allocation_quality(rows: list[dict]) -> dict:
    n = len(rows)
    q = {"n": n, "sides": {}}
    for side in ("sender", "receiver"):
        kinds = defaultdict(lambda: {"n": 0, "cost": ZERO})
        reasons = defaultdict(lambda: {"n": 0, "cost": ZERO})
        unreg = set()
        for r in rows:
            p = r[side]
            kinds[p["kind"]]["n"] += 1
            kinds[p["kind"]]["cost"] += r["net"]
            if p["kind"] == "unallocated":
                reasons[p["reason"]]["n"] += 1
                reasons[p["reason"]]["cost"] += r["net"]
            elif p["kind"] == "branch" and p.get("registered") is False:
                unreg.add(p["display"])
        conf = kinds["branch"]["n"] + kinds["head_office"]["n"]
        q["sides"][side] = {"kinds": dict(kinds), "reasons": dict(reasons), "confirmed_n": conf, "confirmed_pct": _pct(conf, n),
                            "unallocated_n": kinds["unallocated"]["n"], "unallocated_pct": _pct(kinds["unallocated"]["n"], n),
                            "unallocated_cost": kinds["unallocated"]["cost"], "unregistered": sorted(unreg)}
    both = sum(1 for r in rows if r["sender"]["kind"] != "unallocated" and r["receiver"]["kind"] != "unallocated")
    q["both_confirmed_n"], q["both_confirmed_pct"] = both, _pct(both, n)
    return q


# ------------------------------------------------------------------------------------------------ support + exceptions
def rate_ok(row: dict, rates: dict) -> bool | None:
    first, add = rates.get("first_kg") or [], rates.get("additional_kg") or []
    if not first or not add or row["weight"] is None:
        return None
    k = max(1, math.ceil(row["weight"]))
    return any(row["base"] == Decimal(str(f)) + Decimal(str(a)) * (k - 1) for f in first for a in add)


def support(rows: list[dict], th: dict, rates: dict) -> dict:
    out: dict = {"n": len(rows)}
    n = len(rows)
    net = sum((r["net"] for r in rows), ZERO)
    top = int(th["top_n"])

    def agg(keyf):
        d: dict = {}
        for r in rows:
            k = keyf(r)
            c = d.setdefault(k, {"key": k, "n": 0, "net": ZERO, "kg": ZERO})
            c["n"] += 1
            c["net"] += r["net"]
            c["kg"] += r["weight"] or ZERO
        for c in d.values():
            c["avg_net"] = c["net"] / c["n"]
            c["share"] = _pct(c["net"], net)
        return sorted(d.values(), key=lambda c: (-c["net"], str(c["key"])))
    out["origins"], out["destinations"] = agg(lambda r: r["origin"] or "—")[:top], agg(lambda r: r["destination"] or "—")[:top]
    out["routes"] = agg(lambda r: f"{r['origin'] or '—'} → {r['destination'] or '—'}")[:top]
    out["services"] = agg(lambda r: r["product"] or "—")
    b1, b2, b3 = th["weight_band_1_kg"], th["weight_band_2_kg"], th["weight_band_3_kg"]
    bands = [("le1", None, b1), ("b2", b1, b2), ("b3", b2, b3), ("gt3", b3, None)]
    out["weights"] = []
    for key, lo, hi in bands:
        sel = [r for r in rows if r["weight"] is not None and (lo is None or r["weight"] > lo) and (hi is None or r["weight"] <= hi)]
        s = sum((r["net"] for r in sel), ZERO)
        out["weights"].append({"key": key, "lo": lo, "hi": hi, "n": len(sel), "net": s, "avg_net": s / len(sel) if sel else None,
                               "kg": sum((r["weight"] for r in sel), ZERO)})
    base, other, tax = (sum((r[k] for r in rows), ZERO) for k in ("base", "other", "tax"))
    ratios = {(r["other"] / r["base"]).quantize(Decimal("0.0001")) for r in rows if r["base"]}
    out["charges"] = {"base": base, "other": other, "tax": tax, "net": net, "gross": net + tax, "other_to_base_min": min(ratios) if ratios else None,
                      "other_to_base_max": max(ratios) if ratios else None, "other_to_base_distinct": len(ratios)}
    # exceptions
    med = statistics.median([r["net"] for r in rows]) if rows else None
    flags: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        f = []
        if r["weight"] is not None and r["weight"] > Decimal(str(th["heavy_weight_kg"])):
            f.append("heavy")
        if r["weight"] is not None and r["actual_weight"] is not None and r["weight"] > r["actual_weight"]:
            f.append("volumetric")
        if r["origin"] and r["origin"] == r["destination"]:
            f.append("same_city")
        if r["pickup_on"] and r["pickup_on"].weekday() in (int(th["weekend_day_1"]), int(th["weekend_day_2"])):
            f.append("weekend")
        if (r["pcs"] or 1) > 1:
            f.append("multi_piece")
        if med and r["net"] > med * Decimal(str(th["outlier_cost_multiple"])):
            f.append("cost_outlier")
        if rate_ok(r, rates) is False:
            f.append("rate_off_card")
        if "conflicting" in str(r["sender"].get("reason")) or "conflicting" in str(r["receiver"].get("reason")):
            f.append("allocation_conflict")
        for x in f:
            flags[x].append(r)
    out["exceptions"] = {k: {"n": len(v), "net": sum((r["net"] for r in v), ZERO), "rows": v} for k, v in flags.items()}
    out["rate_check"] = {"checked": n, "off_card": len(flags.get("rate_off_card", []))} if rows and rate_ok(rows[0], rates) is not None else None
    out["volumetric_extra_kg"] = sum((r["weight"] - r["actual_weight"] for r in flags.get("volumetric", [])), ZERO)
    return out


# ------------------------------------------------------------------------------------------------ main analysis
def analyze(all_rows: list[dict], scope_rows: list[dict], th: dict, rates: dict, month: tuple[int, int] | None,
            coverage: tuple[date, date] | None, filtered: bool) -> dict:
    parties = party_table(scope_rows)
    net = sum((r["net"] for r in scope_rows), ZERO)
    tax = sum((r["tax"] for r in scope_rows), ZERO)
    totals = {"n": len(scope_rows), "net": net, "tax": tax, "gross": net + tax, "base": sum((r["base"] for r in scope_rows), ZERO),
              "other": sum((r["other"] for r in scope_rows), ZERO), "kg": sum((r["weight"] or ZERO for r in scope_rows), ZERO),
              "avg_net": net / len(scope_rows) if scope_rows else None, "avg_gross": (net + tax) / len(scope_rows) if scope_rows else None,
              "branches": sum(1 for p in parties if p["kind"] == "branch")}
    ctrl = {"sent_n": sum(p["sent_n"] for p in parties), "recv_n": sum(p["recv_n"] for p in parties),
            "sent_cost": sum((p["sent_cost"] for p in parties), ZERO), "recv_cost": sum((p["recv_cost"] for p in parties), ZERO)}
    ctrl["ok"] = ctrl["sent_n"] == ctrl["recv_n"] == totals["n"] and ctrl["sent_cost"] == ctrl["recv_cost"] == net
    ids = [r["awb"] for r in scope_rows]
    ctrl["duplicate_awb"] = len(ids) - len(set(ids))
    a = {"totals": totals, "parties": parties, "controls": ctrl, "months": months_table(all_rows, coverage), "party_months": party_months(all_rows),
         "allocation": allocation_quality(scope_rows), "support": support(scope_rows, th, rates), "month": month, "filtered": filtered,
         "thresholds": th}
    if month:
        a["mom"] = mom_table(all_rows, month, th)
    return a


# ------------------------------------------------------------------------------------------------ invoice <-> sheet reconciliation
def reconcile(pdf_rows: list[dict], xlsx_rows: list[dict], pdf_totals: dict, xlsx_totals: dict, adjustments: list[dict], tol: float) -> dict:
    t = Decimal(str(tol))
    checks: list[dict] = []

    def add(cid, subject, expected, invoiced, refs=None, group="primary"):
        diff = (invoiced - expected) if isinstance(expected, Decimal) or isinstance(invoiced, Decimal) else invoiced - expected
        ok = abs(diff) <= (t if isinstance(diff, Decimal) else 0)
        checks.append({"id": cid, "group": group, "subject": subject, "expected": expected, "invoiced": invoiced, "diff": diff,
                       "status": "ok" if ok else "diff", "refs": (refs or [])[:8]})
    xi = {r["awb"]: r for r in xlsx_rows}
    pi = {r["awb"]: r for r in pdf_rows}
    only_pdf, only_x = sorted(set(pi) - set(xi)), sorted(set(xi) - set(pi))
    add("lines", "shipments (sheet rows vs invoice lines)", len(xlsx_rows), len(pdf_rows))
    add("awb_missing_in_sheet", "invoice lines missing from the sheet", 0, len(only_pdf), only_pdf)
    add("awb_missing_in_invoice", "sheet rows missing from the invoice", 0, len(only_x), only_x)
    both = sorted(set(pi) & set(xi))
    bad_base = [a for a in both if pi[a]["base"] != xi[a]["base"]]
    bad_other = [a for a in both if pi[a]["other"] != xi[a]["other"]]
    bad_w = [a for a in both if pi[a]["weight"] != xi[a]["weight"]]
    bad_route = [a for a in both if normalize_text(pi[a]["route_text"]) != normalize_text(f"{xi[a]['origin']} {xi[a]['destination']}")]
    bad_net = [a for a in both if pi[a]["net"] != xi[a]["base"] + xi[a]["other"]]
    add("base_per_awb", "base charge per AWB differs", 0, len(bad_base), bad_base)
    add("other_per_awb", "other charges per AWB differ", 0, len(bad_other), bad_other)
    add("net_per_awb", "invoice line net ≠ sheet base + other", 0, len(bad_net), bad_net)
    add("weight_per_awb", "billed weight per AWB differs", 0, len(bad_w), bad_w)
    add("route_per_awb", "origin / destination text differs", 0, len(bad_route), bad_route, "supporting")
    sp = lambda k: sum((r[k] for r in pdf_rows), ZERO)
    sx = lambda k: sum((r[k] for r in xlsx_rows), ZERO)
    adj_tax = sum((a["tax"] for a in adjustments), ZERO)
    add("sum_base", "Σ base charge", sx("base"), sp("base"))
    add("sum_other", "Σ other charges", sx("other"), sp("other"))
    if "net" in pdf_totals:
        add("net_total", "Total Net Amount (invoice) vs Σ sheet base + other", sx("base") + sx("other"), pdf_totals["net"])
    if "vat" in pdf_totals:
        add("vat_total", "VAT (invoice) vs Σ sheet tax + adjustment", sx("tax") + adj_tax, pdf_totals["vat"])
    if "total" in pdf_totals:
        add("grand_total", "Total invoice amount vs Σ sheet total incl. tax + adjustment", sx("gross") + sum((a["net"] for a in adjustments), ZERO), pdf_totals["total"])
    if xlsx_totals.get("gross") is not None:
        add("sheet_total_row", "Sheet total row vs the invoice total", pdf_totals.get("total", ZERO), xlsx_totals["gross"], group="supporting")
    prim = [c for c in checks if c["group"] == "primary"]
    s = {"ok": sum(1 for c in prim if c["status"] == "ok"), "diff": sum(1 for c in prim if c["status"] == "diff"),
         "supporting_diff": sum(1 for c in checks if c["group"] != "primary" and c["status"] == "diff")}
    return {"checks": checks, "summary": s, "only_pdf": only_pdf, "only_xlsx": only_x}
