#!/usr/bin/env python3
"""WinMart crawler — LIVE. Searches the internal API per basket SKU, matches by
name (shared matcher in lib_match), writes real details + current price into
data/db/products.json.

WinMart API is reachable from the cloud (no token). Store pinned 1535/1998.
Search is loosely ranked, so lib_match scores candidates and rejects bad hits.
Fields confirmed live 2026-07-04 (see CLAUDE.md field map).

Usage:  python scripts/crawl_winmart.py [--limit N] [--min-score 0.5]
"""
import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import lib_db
import lib_match as M

ROOT = Path(__file__).resolve().parent.parent
SEARCH = "https://api-crownx.winmart.vn/it/api/web/v3/item/search"
STORE_CODE = 1535
STORE_GROUP_CODE = 1998
PACE = 1.4  # seconds between requests — polite
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
HEADERS = {"origin": "https://winmart.vn", "referer": "https://winmart.vn/",
           "user-agent": UA, "accept": "application/json"}


def search(term: str, page_size: int = 20) -> list:
    q = urllib.parse.urlencode({"search": term, "storeCode": STORE_CODE,
                                "storeGroupCode": STORE_GROUP_CODE,
                                "pageNumber": 1, "pageSize": page_size})
    try:
        req = urllib.request.Request(f"{SEARCH}?{q}", headers=HEADERS)
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode()).get("data") or []
    except Exception as e:  # noqa: BLE001 — a network hiccup shouldn't kill the run
        print(f"  ! search failed for {term!r}: {e}", file=sys.stderr)
        return []


def to_chain_obj(item: dict, cand: dict) -> dict:
    price = int(cand.get("price") or 0)
    sale = cand.get("salePrice")
    promo = int(sale) if sale and int(sale) < price else None
    pay = promo or price
    dv = item["don_vi_chuan"]
    denom = M.parse_net(cand.get("name", ""), dv)   # real pack size from the name
    if denom is None:
        uom = (cand.get("uomName") or "").lower()
        qpu = cand.get("quantityPerUnit") or 0
        unit_match = (dv == "kg" and uom in ("kg",)) or (dv in ("lít", "lit") and uom in ("lít", "lit", "l"))
        denom = qpu if (unit_match and qpu) else item["quy_doi"]["winmart"]
    seo = cand.get("seoName")
    return {
        "ten_hien_thi": cand.get("name"), "thuong_hieu": cand.get("brandName"),
        "danh_muc": cand.get("categoryName") or cand.get("mch3Name"),
        "hinh_anh": cand.get("mediaUrl"),
        "url": f"https://winmart.vn/products/{seo}" if seo else None,
        "don_vi": cand.get("uomName"), "net": denom,
        "gia_niem_yet": price, "gia_khuyen_mai": promo,
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
        for term in M.search_terms(item):
            cands = [c for c in search(term) if (c.get("quantity") or 0) > 0]
            time.sleep(PACE)
            cand, s = M.best_match(item, cands, name_key="name", min_score=args.min_score)
            if cand and s > best_s:
                best, best_s, used = cand, s, term
            if best is not None:
                break
        if best:
            lib_db.upsert_chain(db, item["id"], item, "winmart", to_chain_obj(item, best))
            matched += 1
            print(f"[{i:2}/{len(basket)}] ✓ {item['id']:24} → {best['name'][:38]:38} (s{best_s:.2f} «{used}»)")
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
