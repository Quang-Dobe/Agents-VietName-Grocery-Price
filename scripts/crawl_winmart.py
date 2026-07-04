#!/usr/bin/env python3
"""WinMart crawler — LIVE. Searches the internal API per basket SKU, matches by
name, writes real details + current price into data/db/products.json.

WinMart API is reachable from the cloud (no token). Store pinned 1535/1998.
Search is loosely ranked, so we score candidates and reject bad hits. Fields
confirmed live 2026-07-04 (see CLAUDE.md field map).

Matching precision/recall levers:
- search BOTH the accented and deaccented term (the API misses some accented
  queries, e.g. "đường" returns nothing but "duong" finds sugar);
- optional per-SKU curation in basket.json: `"match": {"kw": [...], "must": [...]}`
  — kw are search terms to try first, must are tokens a candidate MUST contain;
- đơn giá chuẩn uses the pack size PARSED FROM THE PRODUCT NAME when present, so a
  "can 5L" is priced per real litre, not per the basket's assumed pack.

Usage:  python scripts/crawl_winmart.py [--limit N] [--min-score 0.5]
"""
import argparse
import json
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

import lib_db

ROOT = Path(__file__).resolve().parent.parent
SEARCH = "https://api-crownx.winmart.vn/it/api/web/v3/item/search"
STORE_CODE = 1535
STORE_GROUP_CODE = 1998
PACE = 1.4  # seconds between requests — polite
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
HEADERS = {"origin": "https://winmart.vn", "referer": "https://winmart.vn/",
           "user-agent": UA, "accept": "application/json"}

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


def _clean(w: str) -> str:
    return re.sub(r"[^a-z0-9]", "", deaccent(w).lower())


def _word_ok(w: str) -> bool:
    c = _clean(w)
    if len(c) < 2 or c.isdigit() or SIZE_TOKEN.match(c) or c in DROP:
        return False
    return True


def kept_words(ten_chuan: str) -> list:
    return [w for w in ten_chuan.split() if _word_ok(w)]


def search_terms(item: dict) -> list:
    """Curated kw first, then derived accented (specific→general), then deaccented."""
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
    return [_clean(w) for w in (s or "").split() if _word_ok(w)]


def size_hint(ten_chuan: str) -> str:
    m = re.search(r"\d+[.,]?\d*\s*(kg|g|ml|l|lít|lit)\b", deaccent(ten_chuan).lower())
    return re.sub(r"\s+", "", m.group(0)) if m else ""


def parse_net(name: str, don_vi_chuan: str):
    """Pack size in `don_vi_chuan` units, parsed from the product name.
    Returns a float or None. Handles kg/g and lít/l/ml."""
    n = deaccent(name or "").lower()
    if don_vi_chuan == "kg":
        m = re.search(r"(\d+[.,]?\d*)\s*kg\b", n)
        if m:
            return float(m.group(1).replace(",", "."))
        m = re.search(r"(\d+[.,]?\d*)\s*g\b", n)
        if m:
            return float(m.group(1).replace(",", ".")) / 1000.0
    if don_vi_chuan in ("lít", "lit"):
        m = re.search(r"(\d+[.,]?\d*)\s*ml", n)  # ml first; no \b (names have "220mll" typos)
        if m:
            return float(m.group(1).replace(",", ".")) / 1000.0
        m = re.search(r"(\d+[.,]?\d*)\s*l(?:it)?\b", n)
        if m:
            return float(m.group(1).replace(",", "."))
    return None


def accept(item: dict, cand_name: str) -> bool:
    """A candidate is acceptable if it carries the required product words and no
    derivative-product word. `must` (curated) overrides the default of "the two
    leading product words"."""
    a, b = tokens(item["ten_chuan"]), set(tokens(cand_name))
    if not a or not b:
        return False
    m = item.get("match") or {}
    must = m.get("must")
    need = [_clean(x) for x in must] if must else (a[:2] if len(a) >= 2 else a[:1])
    if not all(t in b for t in need):
        return False
    if m.get("head_start"):  # candidate name must LEAD with our head noun
        cb = tokens(cand_name)
        if not cb or cb[0] != a[0]:
            return False
    dn = " " + re.sub(r"\s+", " ", deaccent(cand_name).lower()) + " "
    avoid = (item.get("match") or {}).get("avoid", [])
    if any(deaccent(w).lower() in dn for w in avoid):
        return False
    return not any(w in dn for w in BLOCK)


def score(item: dict, cand_name: str) -> float:
    a, b = tokens(item["ten_chuan"]), tokens(cand_name)
    bset = set(b)
    if not a or not bset:
        return 0.0
    s = len(set(a) & bset) / len(set(a))
    if b and b[0] == a[0]:  # candidate name leads with our product head noun
        s += 0.3            # e.g. "Chuối tây" beats "Sữa … vị chuối"
    hint = size_hint(item["ten_chuan"])
    if hint and hint in _clean(cand_name):
        s += 0.25
    return s


def http_get(url: str) -> dict:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def search(term: str, page_size: int = 20) -> list:
    q = urllib.parse.urlencode({"search": term, "storeCode": STORE_CODE,
                                "storeGroupCode": STORE_GROUP_CODE,
                                "pageNumber": 1, "pageSize": page_size})
    try:
        return http_get(f"{SEARCH}?{q}").get("data") or []
    except Exception as e:  # noqa: BLE001 — a network hiccup shouldn't kill the run
        print(f"  ! search failed for {term!r}: {e}", file=sys.stderr)
        return []


def to_chain_obj(item: dict, cand: dict) -> dict:
    price = int(cand.get("price") or 0)
    sale = cand.get("salePrice")
    promo = int(sale) if sale and int(sale) < price else None
    pay = promo or price
    don_vi_chuan = item["don_vi_chuan"]
    # denominator for đơn giá chuẩn: real net parsed from name > item net (if unit
    # matches) > basket quy_doi. This keeps unit price right across pack sizes.
    denom = parse_net(cand.get("name", ""), don_vi_chuan)
    if denom is None:
        uom = (cand.get("uomName") or "").lower()
        qpu = cand.get("quantityPerUnit") or 0
        unit_match = (don_vi_chuan == "kg" and uom in ("kg",)) or \
                     (don_vi_chuan in ("lít", "lit") and uom in ("lít", "lit", "l"))
        denom = qpu if (unit_match and qpu) else item["quy_doi"]["winmart"]
    seo = cand.get("seoName")
    return {
        "ten_hien_thi": cand.get("name"),
        "thuong_hieu": cand.get("brandName"),
        "danh_muc": cand.get("categoryName") or cand.get("mch3Name"),
        "hinh_anh": cand.get("mediaUrl"),
        "url": f"https://winmart.vn/products/{seo}" if seo else None,
        "don_vi": cand.get("uomName"),
        "net": denom,
        "gia_niem_yet": price,
        "gia_khuyen_mai": promo,
        "don_gia_chuan": round(pay / denom) if denom else pay,
        "trang_thai": "in_stock" if (cand.get("quantity") or 0) > 0 and pay > 0 else "out_of_stock",
        "nguon": "api",
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--min-score", type=float, default=0.5)
    args = ap.parse_args()

    basket = json.loads((ROOT / "basket.json").read_text())["items"]
    if args.limit:
        basket = basket[: args.limit]
    db = lib_db.load_products()

    matched = 0
    for i, item in enumerate(basket, 1):
        best, best_s, used = None, 0.0, ""
        for term in search_terms(item):
            cands = search(term)
            time.sleep(PACE)
            if not cands:
                continue
            for c in cands:
                if (c.get("quantity") or 0) <= 0 or not accept(item, c.get("name", "")):
                    continue
                s = score(item, c.get("name", ""))
                if s > best_s:
                    best, best_s, used = c, s, term
            if best is not None:
                break
        if best and best_s >= args.min_score:
            obj = to_chain_obj(item, best)
            lib_db.upsert_chain(db, item["id"], item, "winmart", obj)
            matched += 1
            print(f"[{i:2}/{len(basket)}] ✓ {item['id']:24} → {best['name'][:38]:38} "
                  f"{obj['don_gia_chuan']:>8}đ/{item['don_vi_chuan']:3} (s{best_s:.2f} «{used}»)")
        else:
            lib_db.upsert_chain(db, item["id"], item, "winmart",
                                {"trang_thai": "out_of_stock", "nguon": "api",
                                 "_note": f"no confident match (best {best_s:.2f})"})
            print(f"[{i:2}/{len(basket)}] · {item['id']:24} → no match")

    lib_db.save_products(db, updated=None)
    lib_db.set_store("winmart", {"storeCode": STORE_CODE, "storeGroupCode": STORE_GROUP_CODE,
                                 "ten": "WinMart (pinned PoC store)", "dia_chi": None,
                                 "khu_vuc": "TP.HCM"}, updated=None)
    print(f"\nWinMart: matched {matched}/{len(basket)} SKUs → data/db/products.json")


if __name__ == "__main__":
    main()
