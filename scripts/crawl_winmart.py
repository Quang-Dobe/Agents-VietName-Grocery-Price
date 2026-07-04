#!/usr/bin/env python3
"""WinMart crawler — LIVE. Searches the internal API per basket SKU, matches by
name, writes real details + current price into data/db/products.json.

WinMart API is reachable from the cloud (no token). Store pinned 1535/1998.
Search is loosely ranked, so we score candidates and reject bad hits. Fields
confirmed live 2026-07-04 (see CLAUDE.md field map).

Usage:  python scripts/crawl_winmart.py            # crawl whole basket
        python scripts/crawl_winmart.py --limit 5  # first N SKUs (smoke test)
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
PACE = 1.6  # seconds between requests — polite (≤ 1 / 2–3 s target)
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
HEADERS = {"origin": "https://winmart.vn", "referer": "https://winmart.vn/",
           "user-agent": UA, "accept": "application/json"}

# packaging + unit words dropped from keywords / scoring tokens (deaccented).
# NOTE: avoid words that collide with real product words after deaccenting —
# "bo" (bó=bunch) collides with bò=beef, "cai" (cái=unit) collides with Cải=greens,
# so they are intentionally NOT dropped.
DROP = {"tui", "chai", "khay", "goi", "hop", "loc", "lo",
        "cuon", "hu", "vien", "combo", "set", "kg", "g", "ml", "l", "lit",
        "qua", "lon", "thung", "khong"}
SIZE_TOKEN = re.compile(r"^\d+[.,]?\d*(kg|g|ml|l|lit|qua|cuon|hop|goi|loc|khay|tui|chai|con|vi|lon)?$")


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
    """Original (accented) product/brand words, sizes & packaging removed."""
    return [w for w in ten_chuan.split() if _word_ok(w)]


def keyword_variants(ten_chuan: str) -> list:
    """Specific → general search terms; first non-empty result wins."""
    kw = kept_words(ten_chuan)
    out, seen = [], set()
    for n in (3, 2, 1):
        v = " ".join(kw[:n])
        if v and v.lower() not in seen:
            seen.add(v.lower())
            out.append(v)
    return out


def tokens(s: str) -> list:
    return [_clean(w) for w in (s or "").split() if _word_ok(w)]


def size_hint(ten_chuan: str) -> str:
    m = re.search(r"\d+[.,]?\d*\s*(kg|g|ml|l|lít|lit)\b", deaccent(ten_chuan).lower())
    return re.sub(r"\s+", "", m.group(0)) if m else ""


# words that signal a DERIVATIVE product, not the raw item we want
BLOCK = ["sot ", "xot ", "banh ", "cracker", "kim chi", "bao tu", "u muoi",
         "thung ", "snack", "cha bong", "dau goi", "sua tam", "kem "]


def accept(ten_chuan: str, cand_name: str) -> bool:
    """High-precision gate: the two leading product words must both appear, and no
    derivative-product word may be present. Rejects thịt-bò→thịt-heo, cà-chua→sốt,
    táo→bánh, chuối→sữa-chuối, etc."""
    a, b = tokens(ten_chuan), set(tokens(cand_name))
    if not a or not b:
        return False
    need = a[:2] if len(a) >= 2 else a[:1]
    if not all(t in b for t in need):
        return False
    dn = " " + re.sub(r"\s+", " ", deaccent(cand_name).lower()) + " "
    return not any(w in dn for w in BLOCK)


def score(ten_chuan: str, cand_name: str) -> float:
    a, b = tokens(ten_chuan), set(tokens(cand_name))
    if not a or not b:
        return 0.0
    s = len(set(a) & b) / len(set(a))
    hint = size_hint(ten_chuan)
    if hint and hint in _clean(cand_name):  # prefer the right pack size
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


def to_chain_obj(item: dict, don_vi_chuan: str, quy_doi: float) -> dict:
    price = int(item.get("price") or 0)
    sale = item.get("salePrice")
    promo = int(sale) if sale and int(sale) < price else None
    pay = promo or price
    qpu = item.get("quantityPerUnit") or 0
    uom = (item.get("uomName") or "").lower()
    # price per don_vi_chuan: use the item's own net when the unit matches, else quy_doi
    unit_match = (don_vi_chuan == "kg" and uom in ("kg",)) or \
                 (don_vi_chuan in ("lít", "lit") and uom in ("lít", "lit", "l"))
    denom = qpu if (unit_match and qpu) else quy_doi
    seo = item.get("seoName")
    return {
        "ten_hien_thi": item.get("name"),
        "thuong_hieu": item.get("brandName"),
        "danh_muc": item.get("categoryName") or item.get("mch3Name"),
        "hinh_anh": item.get("mediaUrl"),
        "url": f"https://winmart.vn/products/{seo}" if seo else None,
        "don_vi": item.get("uomName"),
        "net": qpu or None,
        "gia_niem_yet": price,
        "gia_khuyen_mai": promo,
        "don_gia_chuan": round(pay / denom) if denom else pay,
        "trang_thai": "in_stock" if (item.get("quantity") or 0) > 0 and pay > 0 else "out_of_stock",
        "nguon": "api",
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--min-score", type=float, default=0.34)
    args = ap.parse_args()

    basket = json.loads((ROOT / "basket.json").read_text())["items"]
    if args.limit:
        basket = basket[: args.limit]
    db = lib_db.load_products()

    matched = 0
    for i, item in enumerate(basket, 1):
        variants = keyword_variants(item["ten_chuan"])
        best, best_s, used = None, 0.0, ""
        for term in variants:
            cands = search(term)
            time.sleep(PACE)
            if not cands:
                continue
            for c in cands:
                if (c.get("quantity") or 0) <= 0:
                    continue
                if not accept(item["ten_chuan"], c.get("name", "")):
                    continue
                s = score(item["ten_chuan"], c.get("name", ""))
                if s > best_s:
                    best, best_s, used = c, s, term
            if best is not None:
                break  # accepted a confident match; stop broadening
        if best and best_s >= args.min_score:
            obj = to_chain_obj(best, item["don_vi_chuan"], item["quy_doi"]["winmart"])
            lib_db.upsert_chain(db, item["id"], item, "winmart", obj)
            matched += 1
            print(f"[{i:2}/{len(basket)}] ✓ {item['id']:24} → {best['name'][:40]:40} "
                  f"{obj['don_gia_chuan']:>8}đ/{item['don_vi_chuan']:3} (s{best_s:.2f} «{used}»)")
        else:
            lib_db.upsert_chain(db, item["id"], item, "winmart",
                                {"trang_thai": "out_of_stock", "nguon": "api",
                                 "_note": f"no confident match (best {best_s:.2f})"})
            print(f"[{i:2}/{len(basket)}] · {item['id']:24} → no match (tried {variants})")

    lib_db.save_products(db, updated=None)  # captured week stamped by the orchestrator
    lib_db.set_store("winmart", {"storeCode": STORE_CODE, "storeGroupCode": STORE_GROUP_CODE,
                                 "ten": "WinMart (pinned PoC store)", "dia_chi": None,
                                 "khu_vuc": "TP.HCM"}, updated=None)
    print(f"\nWinMart: matched {matched}/{len(basket)} SKUs → data/db/products.json")


if __name__ == "__main__":
    main()
