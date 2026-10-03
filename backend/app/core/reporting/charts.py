"""Chart specs -> PNG (matplotlib), shared by every module's PDF report.

Rules: one y-axis (never dual), thin marks, recessive grid, direct value labels only where few, fixed categorical order
(series 1 blue, series 2 orange), single-hue sequential ramp for magnitude (heatmap), text in ink colors, never in
series colors. Arabic text is shaped (arabic-reshaper + bidi) and drawn with DejaVu Sans, which ships with matplotlib."""
import io
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib as mpl  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402

INK, INK2, MUTED, GRID, AXIS = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
SEQ = LinearSegmentedColormap.from_list("seq", ["#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"])
UP, DOWN = "#d03b3b", "#256abf"  # increase of spend / decrease of spend
FONT_DIR = Path(mpl.get_data_path()) / "fonts" / "ttf"
_ARABIC = re.compile("[؀-ۿ]")


def _has_raqm() -> bool:
    from matplotlib import ft2font
    return hasattr(ft2font, "__libraqm_version__")


def shape(text, lang: str = "en") -> str:
    """Text for matplotlib. Current matplotlib wheels bundle libraqm, which shapes and reorders Arabic itself, so the
    logical string is passed through; only without raqm do we shape + apply bidi ourselves."""
    s = "" if text is None else str(text)
    if not _ARABIC.search(s) or _has_raqm():
        return s
    import arabic_reshaper
    from bidi.algorithm import get_display
    return get_display(arabic_reshaper.reshape(s))


def _setup(lang: str):
    mpl.rcParams.update({
        "font.family": "DejaVu Sans", "axes.edgecolor": AXIS, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
        "text.color": INK, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID,
        "grid.linewidth": 0.6, "axes.axisbelow": True, "figure.facecolor": "white", "axes.facecolor": "white"})


def _k(v: float) -> str:
    a = abs(v)
    return f"{v/1e6:.1f}M" if a >= 1e6 else (f"{v/1e3:.0f}k" if a >= 1e4 else f"{v:,.0f}")


def _png(fig) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=170, bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()


def render_chart(spec: dict, lang: str = "en") -> bytes:
    _setup(lang)
    kind = spec["type"]
    fn = {"bar": _bar, "pareto": _pareto, "heatmap": _heatmap, "waterfall": _waterfall, "line": _line}[kind]
    return fn(spec, lang)


def _title(ax, spec, lang):
    ax.set_title(shape(spec["title"], lang), loc="right" if lang == "ar" else "left", fontsize=10.5, color=INK, pad=10)


def _bar(spec, lang):
    x = [shape(v, lang) for v in spec["x"]]
    series = spec["series"]
    horizontal = spec.get("horizontal")
    h = max(2.6, 0.32 * len(x) + 0.9) if horizontal else 3.2
    fig, ax = plt.subplots(figsize=(7.4, h))
    n = len(x)
    if horizontal:
        pos = list(range(n))[::-1]
        for s_i, s in enumerate(series):
            ax.barh(pos, s["values"], color=SERIES[s_i], height=0.62, label=shape(s["name"], lang))
        ax.set_yticks(pos, x)
        for p, v in zip(pos, series[0]["values"]):
            ax.text(v, p, " " + _k(v), va="center", fontsize=7.5, color=INK2)
        ax.grid(axis="y", visible=False)
        ax.xaxis.set_major_formatter(lambda v, _: _k(v))
    else:
        bottoms = [0.0] * n
        w = 0.62 if spec.get("stacked") or len(series) == 1 else 0.8 / len(series)
        for s_i, s in enumerate(series):
            if spec.get("stacked"):
                ax.bar(range(n), s["values"], bottom=bottoms, color=SERIES[s_i], width=w, label=shape(s["name"], lang),
                       edgecolor="white", linewidth=1)
                bottoms = [b + v for b, v in zip(bottoms, s["values"])]
            else:
                ax.bar([i + (s_i - (len(series) - 1) / 2) * w for i in range(n)], s["values"], color=SERIES[s_i], width=w,
                       label=shape(s["name"], lang))
        if len(series) == 1 and n <= 14:
            for i, v in enumerate(series[0]["values"]):
                ax.text(i, v, _k(v), ha="center", va="bottom", fontsize=7.5, color=INK2)
        rot = n > 8 or max((len(v) for v in x), default=0) > 11
        ax.set_xticks(range(n), x, rotation=30 if rot else 0, ha="right" if rot else "center", fontsize=8)
        ax.grid(axis="x", visible=False)
        ax.yaxis.set_major_formatter(lambda v, _: _k(v))
    if len(series) > 1:
        ax.legend(frameon=False, fontsize=8, loc="upper left" if lang != "ar" else "upper right")
    _title(ax, spec, lang)
    return _png(fig)


def _line(spec, lang):
    fig, ax = plt.subplots(figsize=(7.4, 3.2))
    for i, s in enumerate(spec["series"]):
        ax.plot(range(len(spec["x"])), s["values"], color=SERIES[i], linewidth=2, marker="o", markersize=4, label=shape(s["name"], lang))
    ax.set_xticks(range(len(spec["x"])), [shape(v, lang) for v in spec["x"]], fontsize=8)
    ax.yaxis.set_major_formatter(lambda v, _: _k(v))
    if len(spec["series"]) > 1:
        ax.legend(frameon=False, fontsize=8)
    _title(ax, spec, lang)
    return _png(fig)


def _pareto(spec, lang):
    x = [shape(v, lang) for v in spec["x"]]
    fig, ax = plt.subplots(figsize=(7.4, 3.6))
    n = len(x)
    ax.bar(range(n), spec["values"], color=SERIES[0], width=0.62)
    ax.set_xticks(range(n), x, rotation=45, ha="right", fontsize=7.5)
    ax.yaxis.set_major_formatter(lambda v, _: _k(v))
    ax.grid(axis="x", visible=False)
    ax2 = ax.twinx()  # same quantity as a share of the total: a cumulative share, not a second measure
    ax2.plot(range(n), spec["cum"], color=INK2, linewidth=1.6, marker="o", markersize=3)
    ax2.set_ylim(0, 105)
    ax2.set_yticks([0, 25, 50, 75, 100], ["0%", "25%", "50%", "75%", "100%"])
    ax2.grid(False)
    ax2.spines["right"].set_visible(True)
    ax2.spines["right"].set_color(AXIS)
    _title(ax, spec, lang)
    return _png(fig)


def _heatmap(spec, lang):
    rows, cols, vals = spec["rows"], spec["cols"], spec["values"]
    fig, ax = plt.subplots(figsize=(7.4, max(2.6, 0.34 * len(rows) + 1.3)))
    import numpy as np
    m = np.array([[np.nan if v is None else v for v in r] for r in vals], dtype=float)
    ax.imshow(np.ma.masked_invalid(m), cmap=SEQ, aspect="auto")
    ax.set_xticks(range(len(cols)), [shape(c, lang) for c in cols], rotation=45 if len(cols) > 7 else 0, ha="right" if len(cols) > 7 else "center", fontsize=7.5)
    ax.set_yticks(range(len(rows)), [shape(r, lang) for r in rows], fontsize=7.5)
    ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)
    top = np.nanmax(m) if m.size and not np.all(np.isnan(m)) else 1
    for i in range(m.shape[0]):
        for j in range(m.shape[1]):
            if not np.isnan(m[i, j]):
                ax.text(j, i, _k(m[i, j]), ha="center", va="center", fontsize=6.5, color="white" if m[i, j] > top * 0.55 else INK)
    _title(ax, spec, lang)
    return _png(fig)


def _waterfall(spec, lang):
    start, end = spec["start"], spec["end"]
    names = [shape(start[0], lang)] + [shape(v, lang) for v in spec["x"]] + [shape(spec.get("other_label", "…"), lang)] + [shape(end[0], lang)]
    deltas = spec["values"] + [spec["other"]]
    fig, ax = plt.subplots(figsize=(7.4, 3.5))
    level = start[1]
    ax.bar(0, start[1], color=SERIES[0], width=0.6)
    for i, d in enumerate(deltas, 1):
        ax.bar(i, d, bottom=level if d >= 0 else level + d, color=UP if d > 0 else DOWN, width=0.6)
        ax.text(i, max(level, level + d), f"{d:+,.0f}".replace(",000", "k") if abs(d) < 1e4 else f"{d/1e3:+.0f}k", ha="center", va="bottom", fontsize=7, color=INK2)
        level += d
    ax.bar(len(deltas) + 1, end[1], color=SERIES[0], width=0.6)
    ax.set_xticks(range(len(names)), names, rotation=45, ha="right", fontsize=7.5)
    ax.yaxis.set_major_formatter(lambda v, _: _k(v))
    ax.grid(axis="x", visible=False)
    _title(ax, spec, lang)
    return _png(fig)
