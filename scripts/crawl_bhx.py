#!/usr/bin/env python3
"""Bách Hóa Xanh crawler — runs from a RESIDENTIAL IP (the BHX API resets
datacenter IPs — see docs/research/POC-FINDINGS.md, so this is the local-run path).

BHX has no public search endpoint; it is CATEGORY-based. For each basket group we
fetch the relevant BHX category(ies), then match each SKU against that group's
products with the shared matcher (lib_match, same `match` hints as WinMart). The
token is minted per run with a headless browser (scripts/bhx_token.py).

⚠️ On the FIRST local run, confirm two things (both logged below to make it easy):
  1. the pinned store (provinceId/storeId) — pick a central HCMC store;
  2. the category slugs in BHX_CATS and the product field names in `to_chain_obj`.
The crawler prints the keys of the first product it sees so you can verify fields.

Usage (from home / residential IP):
    python scripts/crawl_bhx.py                 # crawl whole basket
    python scripts/crawl_bhx.py --province 3 --store 2546
    python scripts/crawl_bhx.py --dump          # print first product JSON and exit
"""
import argparse
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import lib_db
import lib_match as M

ROOT = Path(__file__).resolve().parent.parent
API = "https://apibhx.tgdd.vn"
XAPIKEY = "bhx-api-core-2022"
PACE = 2.5  # seconds between requests — polite (BHX is stricter; go slow)
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

# Basket group → BHX category slug(s). ⚠️ CONFIRM these slugs on the first local
# run (the script logs which returned products vs. came back empty). A group may
# span several BHX categories; list them all and we match within the union.
BHX_CATS = {
    "Gạo & lương thực": ["gao", "gao-nep-dau", "mi-hu-tieu-pho-bun-kho"],
    "Thịt heo": ["thit-heo"],
    "Thịt gà": ["thit-ga-vit-chim-cut", "thit-ga"],
    "Thịt bò": ["thit-bo"],
    "Cá & thủy sản": ["ca", "hai-san", "ca-hai-san-tuoi-song"],
    "Trứng": ["trung-cac-loai"],
    "Rau củ": ["rau-la", "cu-qua", "rau-cu"],
    "Trái cây": ["trai-cay"],
    "Dầu ăn": ["dau-an"],
    "Gia vị": ["nuoc-cham-mam", "duong", "muoi", "hat-nem-bot-ngot-bot-canh", "gia-vi"],
    "Sữa": ["sua-tuoi", "sua-dac", "sua-chua-an"],
    "Mì gói": ["mi-an-lien"],
    "Cà phê": ["ca-phe"],
    "Đồ dùng thiết yếu": ["giay-ve-sinh-khan-giay", "nuoc-rua-chen", "bot-giat-nuoc-xa-vai"],
}


def get_headers() -> dict:
    creds = json.loads(subprocess.check_output([sys.executable, str(ROOT / "scripts" / "bhx_token.py")]))
    if not creds.get("token"):
        print("! could not mint a BHX token (browser step failed). "
              "Are you on a residential IP with Chromium installed?", file=sys.stderr)
        sys.exit(2)
    return {
        "Authorization": creds["token"], "deviceid": creds["deviceid"],
        "xapikey": XAPIKEY, "host": "apibhx.tgdd.vn",
        "origin": "https://www.bachhoaxanh.com", "referer": "https://www.bachhoaxanh.com/",
        "user-agent": UA,
    }


def fetch_category(slug: str, province: int, store: int, headers: dict) -> list:
    q = (f"{API}/Category/V2/GetCate?provinceId={province}&wardId=0&districtId=0"
         f"&storeId={store}&categoryUrl={slug}&isMobile=true&isV2=true&pageSize=300")
    try:
        req = urllib.request.Request(q, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode())
        return data.get("data", {}).get("products", []) or []
    except Exception as e:  # noqa: BLE001
        print(f"  ! category {slug!r} failed: {e}", file=sys.stderr)
        return []


def to_chain_obj(item: dict, p: dict) -> dict:
    # ⚠️ CONFIRM these field names against a live product (run with --dump).
    sys_price = int(p.get("sysPrice") or p.get("price") or 0)
    price = int(p.get("price") or sys_price)
    promo = price if 0 < price < sys_price else None
    pay = promo or sys_price
    dv = item["don_vi_chuan"]
    denom = M.parse_net(p.get("name", ""), dv) or p.get("netUnitValue") or item["quy_doi"]["bhx"]
    url = p.get("url") or ""
    if url and not url.startswith("http"):
        url = "https://www.bachhoaxanh.com/" + url.lstrip("/")
    stock = p.get("stockQuantity", p.get("stock", 1))
    return {
        "ten_hien_thi": p.get("name"), "thuong_hieu": p.get("brandName") or p.get("brand"),
        "danh_muc": p.get("category"),
        "hinh_anh": p.get("avatar") or p.get("imgUrl") or (p.get("images") or [None])[0],
        "url": url or None, "don_vi": p.get("unit"), "net": denom,
        "gia_niem_yet": sys_price, "gia_khuyen_mai": promo,
        "don_gia_chuan": round(pay / denom) if denom else pay,
        "trang_thai": "in_stock" if (stock is None or stock > 0) and pay > 0 else "out_of_stock",
        "nguon": "api",
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--province", type=int, default=3)
    ap.add_argument("--store", type=int, default=2546)
    ap.add_argument("--min-score", type=float, default=0.5)
    ap.add_argument("--dump", action="store_true", help="print the first product JSON and exit")
    args = ap.parse_args()

    basket = json.loads((ROOT / "basket.json").read_text())["items"]
    headers = get_headers()

    if args.dump:
        for slug in ("thit-heo", "gao", "rau-la"):
            prods = fetch_category(slug, args.province, args.store, headers)
            if prods:
                print(f"# first product of category {slug!r} — confirm field names:")
                print(json.dumps(prods[0], ensure_ascii=False, indent=2))
                return
            time.sleep(PACE)
        print("no products returned from any probe category — check store/slugs/token")
        return

    # fetch each category once, pool per group
    pools, first_logged = {}, False
    for group, slugs in BHX_CATS.items():
        pool = []
        for slug in slugs:
            prods = fetch_category(slug, args.province, args.store, headers)
            print(f"  cat {slug:32} → {len(prods)} products", file=sys.stderr)
            if prods and not first_logged:
                print("  (first product keys: " + ", ".join(sorted(prods[0].keys())) + ")", file=sys.stderr)
                first_logged = True
            pool.extend(prods)
            time.sleep(PACE)
        pools[group] = pool

    db = lib_db.load_products()
    matched = 0
    for i, item in enumerate(basket, 1):
        pool = [p for p in pools.get(item["nhom"], []) if (p.get("stockQuantity", 1) or 0) != 0]
        cand, s = M.best_match(item, pool, name_key="name", min_score=args.min_score)
        if cand:
            lib_db.upsert_chain(db, item["id"], item, "bhx", to_chain_obj(item, cand))
            matched += 1
            print(f"[{i:2}/{len(basket)}] ✓ {item['id']:24} → {str(cand.get('name'))[:38]:38} (s{s:.2f})")
        else:
            lib_db.upsert_chain(db, item["id"], item, "bhx",
                                {"trang_thai": "out_of_stock", "nguon": "api",
                                 "_note": f"no confident BHX match (best {s:.2f})"})
            print(f"[{i:2}/{len(basket)}] · {item['id']:24} → no match")

    lib_db.save_products(db, updated=None)
    lib_db.set_store("bhx", {"provinceId": args.province, "storeId": args.store,
                             "ten": "BHX (pinned local store)", "dia_chi": None,
                             "khu_vuc": "TP.HCM"}, updated=None)
    print(f"\nBHX: matched {matched}/{len(basket)} SKUs → data/db/products.json")
    if matched == 0:
        print("! 0 matches — likely wrong store, stale token, or category slugs need "
              "confirming. Run `python scripts/crawl_bhx.py --dump` to inspect.", file=sys.stderr)


if __name__ == "__main__":
    main()
