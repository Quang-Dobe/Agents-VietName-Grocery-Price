#!/usr/bin/env python3
"""Fast-path BHX crawler. Agent `crawler-bhx` runs this first, then self-heals.

SKELETON — field names and store IDs are confirmed at PoC and live in CLAUDE.md.
This is the fast path; when it errors or a field is missing, the agent inspects a
live response, fixes the field map / this script, and commits.

Reads basket.json, mints a token via bhx_token.py, pulls each SKU's category from
apibhx.tgdd.vn, matches the basket item, and prints BHX price rows as JSON.
"""
import json
import subprocess
import sys
import time
from pathlib import Path

import urllib.request

API = "https://apibhx.tgdd.vn"
XAPIKEY = "bhx-api-core-2022"
# Pinned store — set at PoC, mirror in CLAUDE.md.
PROVINCE_ID = 3
STORE_ID = 2546
PACE_SECONDS = 2.5  # politeness: <= 1 req / 2-3 s

ROOT = Path(__file__).resolve().parent.parent


def get_headers() -> dict:
    creds = json.loads(subprocess.check_output([sys.executable, str(ROOT / "scripts" / "bhx_token.py")]))
    return {
        "Authorization": creds["token"] or "",
        "deviceid": creds["deviceid"],
        "xapikey": XAPIKEY,
        "origin": "https://www.bachhoaxanh.com",
        "referer": "https://www.bachhoaxanh.com/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    }


def fetch_category(category_url: str, headers: dict) -> list:
    q = (
        f"{API}/Category/V2/GetCate?provinceId={PROVINCE_ID}&wardId=0&districtId=0"
        f"&storeId={STORE_ID}&categoryUrl={category_url}&isMobile=true&isV2=true&pageSize=300"
    )
    req = urllib.request.Request(q, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read().decode())
    return data.get("data", {}).get("products", [])


def to_chain_obj(product: dict, quy_doi: float) -> dict:
    """Build the full products.json chain object: DETAILS + current price.
    CONFIRM these field names against a live product at PoC; fix in CLAUDE.md."""
    gia_niem_yet = int(product.get("sysPrice") or product.get("price") or 0)
    gia_khuyen_mai = int(product["price"]) if product.get("price") and product.get("price") != gia_niem_yet else None
    pay = gia_khuyen_mai or gia_niem_yet
    return {
        # details
        "ten_hien_thi": product.get("name"),
        "thuong_hieu": product.get("brandName") or product.get("brand"),
        "danh_muc": product.get("category"),
        "hinh_anh": product.get("avatar") or product.get("imgUrl") or (product.get("images") or [None])[0],
        "url": product.get("url"),
        "don_vi": product.get("unit"),
        "net": product.get("netUnitValue"),
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
    headers = get_headers()
    db = lib_db.load_products()
    # NOTE: mapping each SKU -> its category slug is part of P1; resolve via the
    # category tree (/Menu/GetMenuV2) and match by product name/slug.
    for item in basket:
        # placeholder: real impl matches `item` inside its category's product list,
        # then: lib_db.upsert_chain(db, item["id"], item, "bhx", to_chain_obj(prod, item["quy_doi"]["bhx"]))
        time.sleep(PACE_SECONDS)
        lib_db.upsert_chain(db, item["id"], item, "bhx",
                            {"trang_thai": "out_of_stock", "nguon": "api", "_todo": "match at P1"})
    lib_db.save_products(db, updated=None)  # set real captured week at P2
    print(f"bhx: wrote {len(basket)} SKU stubs into data/db/products.json")


if __name__ == "__main__":
    main()
