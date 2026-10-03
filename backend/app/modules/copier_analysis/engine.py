"""Deterministic analysis and reconciliation for the copier module. Pure functions: no database, no AI.

Authoritative sources: Part 1 of the monthly statement (operational) and the supplier's e-invoice (financial).
Part 2 / Word are supporting detail; scanned status pages are evidence only and are NOT inputs here.
Costs are *allocated from the invoice's own unit prices* (rent per class, additional-copy rate per class), pre-tax:
the invoice's VAT / withholding exist only at invoice level and are never spread over machines."""
from collections import defaultdict
from decimal import Decimal

ZERO = Decimal("0")
BANDS = (("lt_low", None), ("low_to_50", 50), ("to_100", 100), ("over_100", None))


def _d(v) -> Decimal | None:
    return None if v is None else Decimal(str(v))


def _pct(a, b):
    return float(Decimal(a) / Decimal(b) * 100) if b else None


def class_package(k: str) -> int | None:
    try:
        return int(k.rsplit("_", 1)[1])
    except (ValueError, IndexError):
        return None


def line_applies(line: dict, class_key: str) -> bool:
    """Does an invoice line cover this machine class? (colour/A3/printer words and package sizes in its description)"""
    pkg = class_package(class_key)
    pk = line.get("packages") or []
    if line.get("a3"):
        return class_key.startswith("color_a3_") and (not pk or pkg in pk)
    if line.get("color"):
        return class_key.startswith("color_copier_") and (not pk or pkg in pk)
    if line.get("printers"):
        return class_key.startswith("printer_") and (not pk or pkg in pk)
    return class_key.startswith("mono_copier_") and pkg in pk


def price_book(classes: list[str], lines: list[dict]) -> dict[str, dict]:
    """Per class: the invoice's rent unit price and additional-copy rate (None when the invoice has no such line)."""
    book: dict[str, dict] = {}
    for k in classes:
        rent = [ln for ln in lines if ln["kind"] == "rent" and line_applies(ln, k)]
        exc = [ln for ln in lines if ln["kind"] == "excess" and line_applies(ln, k)]
        book[k] = {"rent": _d(rent[0]["unit_price"]) if len(rent) == 1 else None, "rent_line": rent[0]["line_no"] if len(rent) == 1 else None,
                   "excess_rate": _d(exc[0]["unit_price"]) if len(exc) == 1 else None, "excess_line": exc[0]["line_no"] if len(exc) == 1 else None,
                   "ambiguous": len(rent) > 1 or len(exc) > 1}
    return book


def enrich(machines: list[dict], book: dict[str, dict]) -> list[dict]:
    out = []
    for m in machines:
        pk, cons, exc = m.get("package"), m.get("cons"), m.get("exc")
        b = book.get(m["class_key"], {})
        rent = b.get("rent")
        rate = b.get("excess_rate")
        exc_cost = (Decimal(exc) * rate) if exc is not None and rate is not None else (ZERO if exc == 0 else None)
        cost = (rent + (exc_cost if exc_cost is not None else ZERO)) if rent is not None and (exc_cost is not None or not exc) else None
        out.append({**m, "util": _pct(cons, pk) if cons is not None and pk else None,
                    "unused": max(0, pk - cons) if cons is not None and pk else None, "rent": rent, "excess_cost": exc_cost, "cost": cost})
    return out


def _agg(rows: list[dict]) -> dict:
    cons = sum(r["cons"] or 0 for r in rows)
    alw = sum(r["package"] or 0 for r in rows)
    exc = sum(r["exc"] or 0 for r in rows)
    costed = [r for r in rows if r["cost"] is not None]
    cost = sum((r["cost"] for r in costed), ZERO)
    return {"machines": len(rows), "consumption": cons, "allowance": alw, "utilization": _pct(cons, alw), "excess_pages": exc,
            "in_excess": sum(1 for r in rows if (r["exc"] or 0) > 0), "rent": sum((r["rent"] for r in rows if r["rent"] is not None), ZERO),
            "excess_cost": sum((r["excess_cost"] for r in rows if r["excess_cost"] is not None), ZERO), "cost": cost,
            "cost_complete": len(costed) == len(rows), "cost_per_page": (cost / cons if cons and len(costed) == len(rows) else None),
            "unused": sum(r["unused"] or 0 for r in rows)}


def _group(rows: list[dict], keyf, labelf=None) -> list[dict]:
    g: dict = defaultdict(list)
    for r in rows:
        g[keyf(r)].append(r)
    res = []
    for k, rs in g.items():
        a = _agg(rs)
        a["key"] = k
        a["name"] = labelf(rs) if labelf else k
        res.append(a)
    return res


def analyze_cycle(machines: list[dict], invoice: dict | None, th: dict, filtered: bool = False) -> dict:
    """machines: dicts with class_key, package, branch_key, branch_display, location_group, group_kind, cons, exc, prev, cur, flags."""
    lines = (invoice or {}).get("lines", [])
    classes = sorted({m["class_key"] for m in machines})
    book = price_book(classes, lines) if lines else {k: {"rent": None, "excess_rate": None} for k in classes}
    rows = enrich(machines, book)
    out: dict = {"unsupported": [], "notes": [], "price_book": book}
    out["has_invoice"] = bool(lines)
    out["totals"] = _agg(rows)
    if not lines:
        out["unsupported"] += ["cost", "invoice_reconciliation"]
    out["by_class"] = sorted(_group(rows, lambda r: r["class_key"]), key=lambda a: -a["machines"])
    for a in out["by_class"]:
        a["package"] = class_package(a["key"])
        a["rent_unit"], a["excess_rate"] = book[a["key"]].get("rent"), book[a["key"]].get("excess_rate")
    has_loc = any(r.get("location_group") for r in rows)
    if has_loc:
        loc = _group(rows, lambda r: r.get("location_group") or "—")
        out["by_location"] = sorted(loc, key=lambda a: -a["consumption"])
        out["unassigned_location"] = sum(1 for r in rows if not r.get("location_group"))
    else:
        out["by_location"], out["unassigned_location"] = [], len(rows)
        out["unsupported"].append("location")
    labels: dict[str, dict] = defaultdict(lambda: defaultdict(int))
    for r in rows:
        labels[r["branch_key"]][r["branch_display"]] += 1
    out["by_branch"] = sorted(_group(rows, lambda r: r["branch_key"], lambda rs: max(
        ((x["branch_display"], 1) for x in rs), key=lambda t: sum(1 for y in rs if y["branch_display"] == t[0]))[0]),
        key=lambda a: -a["consumption"])
    for a in out["by_branch"]:
        a["location"] = next((r.get("location_group") for r in rows if r["branch_key"] == a["key"] and r.get("location_group")), None)
        a["classes"] = sorted({r["class_key"] for r in rows if r["branch_key"] == a["key"]})

    # utilisation distribution and lists
    low, vlow, hx = float(th["low_utilization_pct"]), float(th["very_low_utilization_pct"]), float(th["high_excess_pct"])
    known = [r for r in rows if r["util"] is not None]
    out["bands"] = {"almost_unused": sum(1 for r in known if r["util"] < vlow), "under_utilised": sum(1 for r in known if r["util"] < low),
                    "low_to_50": sum(1 for r in known if low <= r["util"] < 50), "50_to_100": sum(1 for r in known if 50 <= r["util"] <= 100),
                    "over_100": sum(1 for r in known if r["util"] > 100), "unknown": len(rows) - len(known)}
    out["under_utilised"] = sorted((r for r in known if r["util"] < low), key=lambda r: r["util"])
    out["exceeding"] = sorted((r for r in rows if (r["exc"] or 0) > 0), key=lambda r: -(r["exc"] or 0))
    out["heavy_excess"] = [r for r in out["exceeding"] if r["package"] and (r["exc"] / r["package"] * 100) >= hx]
    out["top_consumers"] = sorted((r for r in rows if r["cons"] is not None), key=lambda r: -r["cons"])[: int(th["top_n"])]
    out["lowest_util"] = sorted(known, key=lambda r: r["util"])[: int(th["top_n"])]
    out["rows"] = rows
    out["flags"] = {}
    for r in rows:
        for f in r.get("flags", []):
            out["flags"][f] = out["flags"].get(f, 0) + 1

    if not filtered and lines:
        out["reconciliation"] = reconcile(machines, invoice, th)
    return out


# ------------------------------------------------------------------------------------------ reconciliation
def _check(cid: str, subject: str, expected, invoiced, tol, unit="count", refs=None, group="primary") -> dict:
    if expected is None or invoiced is None:
        status, diff = "na", None
    else:
        diff = Decimal(str(invoiced)) - Decimal(str(expected))
        status = "ok" if abs(diff) <= Decimal(str(tol)) else "diff"
    return {"id": cid, "subject": subject, "expected": expected, "invoiced": invoiced, "diff": diff, "status": status, "unit": unit,
            "refs": refs or [], "group": group}


def reconcile(machines: list[dict], invoice: dict, th: dict) -> dict:
    """Statement (Part 1) versus the invoice: classes, quantities, additional copies, unit prices and totals."""
    tol = Decimal(str(th["reconcile_tolerance"]))
    lines = invoice["lines"]
    checks: list[dict] = []
    by_class: dict[str, list[dict]] = defaultdict(list)
    for m in machines:
        by_class[m["class_key"]].append(m)
    expected_amounts: list[Decimal] = []
    unmapped_classes = [k for k in by_class if not any(line_applies(ln, k) for ln in lines)]
    for ln in lines:
        ks = [k for k in by_class if line_applies(ln, k)]
        ref = [f"invoice line {ln['line_no']}"]
        if ln["kind"] == "rent":
            n = sum(len(by_class[k]) for k in ks)
            checks.append(_check(f"rent_qty_{ln['line_no']}", ln["description_short"], n if ks else None, ln["qty"], 0, "machines", ref))
            exp = Decimal(n) * Decimal(str(ln["unit_price"])) if ks and ln["unit_price"] is not None else None
            checks.append(_check(f"rent_amount_{ln['line_no']}", ln["description_short"], exp, ln["sales_total"], tol, "egp", ref))
            if exp is not None:
                expected_amounts.append(exp)
            rents = {m["rent_detail"] for k in ks for m in by_class[k] if m.get("rent_detail") is not None}
            if rents:
                checks.append(_check(f"rent_unit_{ln['line_no']}", ln["description_short"], rents.pop() if len(rents) == 1 else None,
                                     ln["unit_price"], tol, "egp", ref + ["statement Part 2 rental value"], group="supporting"))
        elif ln["kind"] == "excess":
            vals = [m["exc"] for k in ks for m in by_class[k]]
            have = None if (not ks or any(v is None for v in vals)) else sum(vals)
            checks.append(_check(f"excess_qty_{ln['line_no']}", ln["description_short"], have, ln["qty"], 0, "copies", ref))
            exp = Decimal(have) * Decimal(str(ln["unit_price"])) if have is not None and ln["unit_price"] is not None else None
            checks.append(_check(f"excess_amount_{ln['line_no']}", ln["description_short"], exp, ln["sales_total"], tol, "egp", ref))
            if exp is not None:
                expected_amounts.append(exp)
        else:
            checks.append(_check(f"line_kind_{ln['line_no']}", ln["description_short"], None, ln["sales_total"], tol, "egp", ref))
        if ln.get("qty") is not None and ln.get("unit_price") is not None and ln.get("sales_total") is not None:
            checks.append(_check(f"line_arith_{ln['line_no']}", ln["description_short"], Decimal(str(ln["qty"])) * Decimal(str(ln["unit_price"])),
                                 ln["sales_total"], tol, "egp", ref + ["quantity × unit price"], group="invoice_internal"))
    tot = invoice.get("totals", {})
    sales = tot.get("sales_total")
    checks.append(_check("total_expected_sales", "total_sales", sum(expected_amounts, ZERO) if expected_amounts and not unmapped_classes else None,
                         sales, tol, "egp", ["statement quantities × invoice unit prices"]))
    line_sum = sum((Decimal(str(ln["sales_total"])) for ln in lines if ln["sales_total"] is not None), ZERO)
    checks.append(_check("total_line_sum", "total_lines_sum", line_sum, sales, tol, "egp", ["Σ invoice lines"], group="invoice_internal"))
    vat_rates = [ln["vat_rate"] for ln in lines if ln.get("vat_rate") is not None]
    wht_rates = [ln["wht_rate"] for ln in lines if ln.get("wht_rate") is not None]
    vr = Decimal(str(max(set(vat_rates), key=vat_rates.count))) if vat_rates else None
    wr = Decimal(str(max(set(wht_rates), key=wht_rates.count))) if wht_rates else None
    if sales is not None and vr is not None:
        checks.append(_check("total_vat", "total_vat", Decimal(str(sales)) * vr / 100, tot.get("vat"), Decimal("0.05"), "egp",
                             [f"{vr}% of sales"], group="invoice_internal"))
    if sales is not None and wr is not None:
        checks.append(_check("total_wht", "total_wht", Decimal(str(sales)) * wr / 100, tot.get("withholding"), Decimal("0.05"), "egp",
                             [f"{wr}% of sales"], group="invoice_internal"))
    if None not in (sales, tot.get("vat"), tot.get("withholding"), tot.get("grand_total")):
        checks.append(_check("total_grand", "total_grand", Decimal(str(sales)) + Decimal(str(tot["vat"])) - Decimal(str(tot["withholding"])),
                             tot["grand_total"], Decimal("0.05"), "egp", ["sales + VAT − withholding"], group="invoice_internal"))
    primary = [c for c in checks if c["group"] == "primary"]
    return {"checks": checks, "unmapped_classes": unmapped_classes, "unmapped_lines": [ln["line_no"] for ln in lines
                                                                                     if not any(line_applies(ln, k) for k in by_class)],
            "summary": {"ok": sum(1 for c in primary if c["status"] == "ok"), "diff": sum(1 for c in primary if c["status"] == "diff"),
                        "na": sum(1 for c in primary if c["status"] == "na")}}


# ------------------------------------------------------------------------------------------ trend (several cycles)
def analyze_trend(cycles: list[dict], th: dict) -> dict:
    """cycles: [{period:(y,m), totals:{...}, invoice_total, recon:{ok,diff,na}|None, machines:[...]}], oldest first."""
    cycles = sorted(cycles, key=lambda c: c["period"])
    rows = []
    prev = None
    for c in cycles:
        t = c["totals"]
        row = {"period": c["period"], "machines": t["machines"], "consumption": t["consumption"], "allowance": t["allowance"],
               "utilization": t["utilization"], "excess_pages": t["excess_pages"], "rent": t["rent"], "excess_cost": t["excess_cost"],
               "cost": t["cost"] if t["cost_complete"] else None, "invoice_total": c.get("invoice_total"), "recon": c.get("recon")}
        if prev is not None:
            for k in ("consumption", "excess_pages", "cost", "machines"):
                a, b = prev[k], row[k]
                row[f"{k}_mom"] = None if a is None or b is None else (b - a)
                row[f"{k}_mom_pct"] = None if a in (None, 0) or b is None else float((Decimal(str(b)) - Decimal(str(a))) / Decimal(str(a)) * 100)
        rows.append(row)
        prev = row
    # reading continuity: a machine's previous reading should equal last month's current reading
    cont = []
    for a, b in zip(cycles, cycles[1:]):
        last = {(m["class_key"], m["branch_key"], m["cur"]) for m in a["machines"] if m["cur"] is not None}
        matched = sum(1 for m in b["machines"] if (m["class_key"], m["branch_key"], m["prev"]) in last)
        cont.append({"from": a["period"], "to": b["period"], "machines": len(b["machines"]), "continuous": matched,
                     "broken": len(b["machines"]) - matched})
    return {"rows": rows, "continuity": cont, "n": len(cycles), "indicative": len(cycles) < int(th["min_months_for_trend"])}
