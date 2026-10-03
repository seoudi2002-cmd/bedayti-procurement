"""Vehicle identity. A vehicle is its plate as the file writes it (letters + digits, spacing normalised). Different files write it differently
(letters present or not, a letter typed differently); two spellings are linked only by an exact match, by a digits-only source whose number is
unique, or by an approved alias in the `vehicles.plates` setting — never by guessing."""
import re

from app.core.analysis.opsupport import fold

_DIGITS = re.compile(r"(\d{3,5})")


def clean(text) -> str:
    if isinstance(text, float) and text == int(text):
        text = int(text)
    t = " ".join(str(text or "").replace("ـ", "").replace("‏", "").split())
    return t


def key(text) -> str:
    """Comparison key: folded Arabic letters and digits separated by single spaces (display text keeps the file's spelling)."""
    t = fold(clean(text))
    t = re.sub(r"[^\w\s]", " ", t)
    letters = re.findall(r"[^\W\d_]", t)
    digits = "".join(re.findall(r"\d", t))
    return (" ".join(letters) + " " + digits).strip()


def digits(text) -> str:
    m = _DIGITS.findall(clean(text))
    return m[-1] if m else ""


def link(keys: list[str], aliases: dict[str, str] | None = None) -> tuple[dict, list]:
    """Map every plate key seen in any source to a canonical vehicle key; also return candidate pairs that were NOT linked.
    keys: all plate keys seen. Canonical keys are those from the cost statement when present (callers pass them first)."""
    aliases = {key(a): key(b) for a, b in (aliases or {}).items()}
    canon: dict[str, str] = {}
    seen: list[str] = []
    for k in keys:
        k = aliases.get(k, k)
        if k not in seen:
            seen.append(k)
    by_digits: dict[str, list[str]] = {}
    for k in seen:
        if " " in k or re.search(r"[^\W\d_]", k):
            by_digits.setdefault(digits(k), []).append(k)
    cand = []
    for k in keys:
        a = aliases.get(k, k)
        if not re.search(r"[^\W\d_]", a):      # digits only source: linked when exactly one lettered plate carries the number
            hit = [x for x in by_digits.get(digits(a), []) if re.search(r"[^\W\d_]", x)]
            canon[k] = hit[0] if len(hit) == 1 else a
            if len(hit) > 1:
                cand.append((a, hit))
        else:
            canon[k] = a
    for d, ks in by_digits.items():
        if d and len(ks) > 1:
            cand.append((d, ks))
    uniq, seen_c = [], set()
    for d, ks in cand:
        sig = (d, tuple(sorted(ks)))
        if sig not in seen_c:
            seen_c.add(sig)
            uniq.append((d, ks))
    return canon, uniq
