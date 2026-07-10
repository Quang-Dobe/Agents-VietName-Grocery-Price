#!/usr/bin/env python3
"""WinMart FULL CATALOG crawler — LIVE. Separate from crawl_winmart.py (which only
fetches the 40 fixed basket SKUs). This pages through the store's entire online
catalog and writes a current snapshot of every product.

Discovery (2026-07-10): `/it/api/web/v3/item/search` normally filters by the
`search=` query param (used by crawl_winmart.py). Calling it WITHOUT `search`
returns a stable, fully-paginated listing of the whole catalog instead of a
"no results" response — confirmed live: storeCode=1535/storeGroupCode=1998 has
4263 products across ~43 pages at pageSize=100, distinct items per page, no
duplicates across repeated calls. No bearer token needed (same host as the
basket crawler).

Usage:  python scripts/crawl_winmart_full.py [--page-size 100] [--max-pages N] [--pace 1.5]
"""
import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "full" / "winmart-catalog.json"
SEARCH = "https://api-crownx.winmart.vn/it/api/web/v3/item/search"
STORE_CODE = 1535
STORE_GROUP_CODE = 1998
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
HEADERS = {"origin": "https://winmart.vn", "referer": "https://winmart.vn/",
           "user-agent": UA, "accept": "application/json"}


def fetch_page(page_number: int, page_size: int) -> dict:
    q = urllib.parse.urlencode({"storeCode": STORE_CODE, "storeGroupCode": STORE_GROUP_CODE,
                                "pageNumber": page_number, "pageSize": page_size})
    req = urllib.request.Request(f"{SEARCH}?{q}", headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def to_record(cand: dict) -> dict:
    price = cand.get("price") or 0
    sale = cand.get("salePrice")
    price = int(price)
    promo = int(sale) if sale and int(sale) < price else None
    pay = promo or price
    qpu = cand.get("quantityPerUnit") or 0
    seo = cand.get("seoName")
    discount_pct = round((price - pay) / price * 100, 1) if promo and price else None
    return {
        "id": cand.get("itemNo") or cand.get("id"),
        "sku": cand.get("sku"),
        "barcode": cand.get("barcode"),
        "ten": cand.get("name"),
        "thuong_hieu": cand.get("brandName"),
        "danh_muc": cand.get("categoryName") or cand.get("mch3Name"),
        "danh_muc_code": cand.get("categoryCode"),
        "mch": [cand.get(f"mch{i}Name") for i in range(1, 6) if cand.get(f"mch{i}Name")],
        "hinh_anh": cand.get("mediaUrl"),
        "url": f"https://winmart.vn/products/{seo}" if seo else None,
        "don_vi": cand.get("uomName"), "net": qpu or None,
        "gia_niem_yet": price, "gia_khuyen_mai": promo,
        "gia_ban": pay,
        "don_gia": round(pay / qpu) if qpu else None,
        "giam_gia_pct": discount_pct,
        "trang_thai": "in_stock" if (cand.get("quantity") or 0) > 0 and pay > 0 else "out_of_stock",
        "nguon": "api",
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--page-size", type=int, default=100)
    ap.add_argument("--max-pages", type=int, default=0, help="0 = no limit")
    ap.add_argument("--pace", type=float, default=1.5)
    args = ap.parse_args()

    t0 = time.time()
    first = fetch_page(1, args.page_size)
    paging = first.get("paging") or {}
    total_pages = paging.get("totalPages") or 1
    total_count = paging.get("totalCount") or 0
    if args.max_pages:
        total_pages = min(total_pages, args.max_pages)

    print(f"WinMart full catalog: {total_count} items across {paging.get('totalPages')} pages "
          f"(fetching {total_pages}).", file=sys.stderr)

    by_id = {}
    for it in first.get("data") or []:
        rec = to_record(it)
        if rec["id"]:
            by_id[rec["id"]] = rec

    for page in range(2, total_pages + 1):
        time.sleep(args.pace)
        try:
            resp = fetch_page(page, args.page_size)
        except Exception as e:  # noqa: BLE001 — a network hiccup shouldn't kill the run
            print(f"  ! page {page} failed: {e}", file=sys.stderr)
            continue
        for it in resp.get("data") or []:
            rec = to_record(it)
            if rec["id"]:
                by_id[rec["id"]] = rec
        if page % 10 == 0 or page == total_pages:
            print(f"  ...page {page}/{total_pages} ({len(by_id)} items so far)", file=sys.stderr)

    items = sorted(by_id.values(), key=lambda r: r["id"])
    out = {
        "updated": time.strftime("%Y-%m-%d"),
        "store": {"storeCode": STORE_CODE, "storeGroupCode": STORE_GROUP_CODE},
        "total_count": total_count,
        "fetched_count": len(items),
        "items": items,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    elapsed = time.time() - t0
    print(f"Wrote {len(items)}/{total_count} items to {OUT.relative_to(ROOT)} in {elapsed:.0f}s", file=sys.stderr)


if __name__ == "__main__":
    main()
