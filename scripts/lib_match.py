#!/usr/bin/env python3
"""Shared product-matching helpers used by both crawlers.

Store-agnostic: it scores a store product against a basket SKU using the SKU's
optional `match` hints ({kw, must, avoid, head_start}). No network here.
"""
import re
import unicodedata

# packaging + unit words dropped from keywords / scoring tokens (deaccented).
# Avoid words that collide with real product words after deaccenting: "bo" (bó)
# collides with bò=beef, "cai" (cái) with Cải=greens — so they are NOT dropped.
DROP = {"tui", "chai", "khay", "goi", "hop", "loc", "lo",
        "cuon", "hu", "vien", "combo", "set", "kg", "g", "ml", "l", "lit",
        "qua", "lon", "thung", "khong"}
SIZE_TOKEN = re.compile(r"^\d+[.,]?\d*(kg|g|ml|l|lit|qua|cuon|hop|goi|loc|khay|tui|chai|con|vi|lon)?$")

# words that signal a DERIVATIVE product, not the raw item we want
BLOCK = ["sot ", "xot ", "banh ", "cracker", "kim chi", "bao tu", "u muoi",
         "thung ", "snack", "cha bong", "dau goi", "sua tam", "kem ", "keo ",
         "tao bien", "xit ", "spa ", "mat na", "nuoc ngot", "dua hau", " dua ",
         "creamer", "duoi muoi", "diet muoi", "xong ", "nhang", "huong dau",
         "so co la", "socola"]


def deaccent(s: str) -> str:
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.replace("đ", "d").replace("Đ", "D")


def clean(w: str) -> str:
    return re.sub(r"[^a-z0-9]", "", deaccent(w).lower())


def word_ok(w: str) -> bool:
    c = clean(w)
    return not (len(c) < 2 or c.isdigit() or SIZE_TOKEN.match(c) or c in DROP)


def kept_words(ten_chuan: str) -> list:
    return [w for w in ten_chuan.split() if word_ok(w)]


def search_terms(item: dict) -> list:
    """Curated kw first, then derived accented (specific→general), then deaccented.
    Used by search-based stores (WinMart)."""
    out, seen = [], set()

    def add(v):
        v = (v or "").strip()
        if v and v.lower() not in seen:
            seen.add(v.lower())
            out.append(v)

    for kw in (item.get("match") or {}).get("kw", []):
        add(kw)
    kw = kept_words(item["ten_chuan"])
    for n in (3, 2, 1):
        add(" ".join(kw[:n]))
        add(deaccent(" ".join(kw[:n])))
    return out


def tokens(s: str) -> list:
    return [clean(w) for w in (s or "").split() if word_ok(w)]


def size_hint(ten_chuan: str) -> str:
    m = re.search(r"\d+[.,]?\d*\s*(kg|g|ml|l|lít|lit)\b", deaccent(ten_chuan).lower())
    return re.sub(r"\s+", "", m.group(0)) if m else ""


def parse_net(name: str, don_vi_chuan: str):
    """Pack size in `don_vi_chuan` units parsed from the product name (float|None)."""
    n = deaccent(name or "").lower()
    if don_vi_chuan == "kg":
        m = re.search(r"(\d+[.,]?\d*)\s*kg\b", n)
        if m:
            return float(m.group(1).replace(",", "."))
        m = re.search(r"(\d+[.,]?\d*)\s*g\b", n)
        if m:
            return float(m.group(1).replace(",", ".")) / 1000.0
    if don_vi_chuan in ("lít", "lit"):
        m = re.search(r"(\d+[.,]?\d*)\s*ml", n)
        if m:
            return float(m.group(1).replace(",", ".")) / 1000.0
        m = re.search(r"(\d+[.,]?\d*)\s*l(?:it)?\b", n)
        if m:
            return float(m.group(1).replace(",", "."))
    return None


def accept(item: dict, cand_name: str) -> bool:
    """Candidate carries the required product words and no derivative-product word.
    `must` (curated) overrides the default of "the two leading product words";
    `avoid` disqualifies; `head_start` requires the name to lead with the head noun."""
    a, b = tokens(item["ten_chuan"]), set(tokens(cand_name))
    if not a or not b:
        return False
    m = item.get("match") or {}
    must = m.get("must")
    need = [clean(x) for x in must] if must else (a[:2] if len(a) >= 2 else a[:1])
    if not all(t in b for t in need):
        return False
    if m.get("head_start"):
        cb = tokens(cand_name)
        if not cb or cb[0] != a[0]:
            return False
    dn = " " + re.sub(r"\s+", " ", deaccent(cand_name).lower()) + " "
    if any(deaccent(w).lower() in dn for w in m.get("avoid", [])):
        return False
    return not any(w in dn for w in BLOCK)


def score(item: dict, cand_name: str) -> float:
    a, b = tokens(item["ten_chuan"]), tokens(cand_name)
    bset = set(b)
    if not a or not bset:
        return 0.0
    s = len(set(a) & bset) / len(set(a))
    if b and b[0] == a[0]:          # candidate leads with our head noun
        s += 0.3
    hint = size_hint(item["ten_chuan"])
    if hint and hint in clean(cand_name):
        s += 0.25
    return s


def best_match(item: dict, candidates: list, name_key="name", min_score=0.5):
    """Pick the highest-scoring acceptable, in-stock-agnostic candidate.
    Returns (candidate, score) or (None, 0.0). Stock is checked by the caller."""
    best, best_s = None, 0.0
    for c in candidates:
        nm = c.get(name_key, "") if isinstance(c, dict) else ""
        if not accept(item, nm):
            continue
        s = score(item, nm)
        if s > best_s:
            best, best_s = c, s
    return (best, best_s) if best_s >= min_score else (None, best_s)
