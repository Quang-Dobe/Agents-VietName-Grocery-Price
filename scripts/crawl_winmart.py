#!/usr/bin/env python3
"""Fast-path WinMart crawler. Agent `crawler-winmart` runs this first, then self-heals.

SKELETON — field names/store codes confirmed at PoC, live in CLAUDE.md. WinMart
needs no bearer token in public scrapers; just a browser UA + winmart.vn referer.

Reads basket.json, queries api-crownx.winmart.vn by category slug for the pinned
store, matches basket items, prints WinMart price rows as JSON.
"""
import json
import time
from pathlib import Path

import urllib.request

API = "https://api-crownx.winmart.vn/it/api/web/v3/item/category"
# Pinned store — set at PoC, mirror in CLAUDE.md.
STORE_CODE = 1535
STORE_GROUP_CODE = 1998
PACE_SECONDS = 2.5

ROOT = Path(__file__).resolve().parent.parent

HEADERS = {
    "origin": "https://winmart.vn",
    "referer": "https://winmart.vn/",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "accept": "application/json",
}


def fetch_category(slug: str, page: int = 1) -> list:
    q = (
        f"{API}?orderByDesc=true&pageNumber={page}&pageSize=100"
        f"&slug={slug}&storeCode={STORE_CODE}&storeGroupCode={STORE_GROUP_CODE}"
    )
    req = urllib.request.Request(q, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read().decode())
    # CONFIRM the exact list path at PoC (data.items / data.products / ...).
    return data.get("data", {}).get("items", []) or data.get("data", {}).get("products", [])


def to_chain_obj(product: dict, quy_doi: float) -> dict:
    """Build the full products.json chain object: DETAILS + current price.
    CONFIRM field names against a live item at PoC; fix in CLAUDE.md."""
    gia_niem_yet = int(product.get("price") or 0)
    sale = product.get("salePrice")
    gia_khuyen_mai = int(sale) if sale and int(sale) != gia_niem_yet else None
    pay = gia_khuyen_mai or gia_niem_yet
    seo = product.get("seoName")
    return {
        # details
        "ten_hien_thi": product.get("name"),
        "thuong_hieu": product.get("brand"),
        "danh_muc": product.get("category"),
        "hinh_anh": product.get("image") or product.get("thumbnail"),
        "url": f"https://winmart.vn/products/{seo}" if seo else None,
        "don_vi": product.get("uom") or product.get("uomName"),
        "net": None,
        # price
        "gia_niem_yet": gia_niem_yet,
        "gia_khuyen_mai": gia_khuyen_mai,
        "don_gia_chuan": round(pay / quy_doi) if quy_doi else pay,
        "trang_thai": "in_stock" if pay > 0 else "out_of_stock",
        "nguon": "api",
    }


def main() -> None:
    import lib_db  # writes into data/db/products.json (current-state, overwritten)

    basket = json.loads((ROOT / "basket.json").read_text())["items"]
    db = lib_db.load_products()
    for item in basket:
        # placeholder: real impl matches `item` in its category list, then:
        # lib_db.upsert_chain(db, item["id"], item, "winmart", to_chain_obj(prod, item["quy_doi"]["winmart"]))
        time.sleep(PACE_SECONDS)
        lib_db.upsert_chain(db, item["id"], item, "winmart",
                            {"trang_thai": "out_of_stock", "nguon": "api", "_todo": "match at P1"})
    lib_db.save_products(db, updated=None)  # set real captured week at P2
    print(f"winmart: wrote {len(basket)} SKU stubs into data/db/products.json")


if __name__ == "__main__":
    main()
