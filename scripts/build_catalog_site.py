#!/usr/bin/env python3
"""Publish the full WinMart catalog as static data files for the FE catalog page.

Splits data/full/winmart-catalog.json into fixed-size chunk files under
site/data/catalog/winmart/, plus an index.json manifest (categories, chunk list,
stats). site/catalog.html + assets/catalog.js fetch this folder and do
pagination/filter/sort entirely client-side — no server, no build step.

Usage:  python scripts/build_catalog_site.py [--chunk-size 300]
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "data" / "full" / "winmart-catalog.json"
STATS = ROOT / "data" / "full" / "winmart-catalog-stats.json"
OUT_DIR = ROOT / "site" / "data" / "catalog" / "winmart"

# Fields the FE actually needs — keep chunk files lean.
FE_FIELDS = ["id", "ten", "thuong_hieu", "danh_muc", "hinh_anh", "url", "don_vi",
             "net", "gia_niem_yet", "gia_khuyen_mai", "gia_ban", "don_gia",
             "giam_gia_pct", "trang_thai"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chunk-size", type=int, default=300)
    args = ap.parse_args()

    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    stats = json.loads(STATS.read_text(encoding="utf-8")) if STATS.exists() else {}
    items = catalog.get("items") or []

    if OUT_DIR.exists():
        for f in OUT_DIR.glob("chunk-*.json"):
            f.unlink()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    chunks = [items[i:i + args.chunk_size] for i in range(0, len(items), args.chunk_size)]
    chunk_files = []
    for i, chunk in enumerate(chunks, start=1):
        name = f"chunk-{i:04d}.json"
        trimmed = [{k: it.get(k) for k in FE_FIELDS} for it in chunk]
        (OUT_DIR / name).write_text(json.dumps(trimmed, ensure_ascii=False) + "\n", encoding="utf-8")
        chunk_files.append(name)

    categories = sorted({it.get("danh_muc") for it in items if it.get("danh_muc")})
    manifest = {
        "updated": catalog.get("updated"),
        "total_count": len(items),
        "chunk_size": args.chunk_size,
        "chunks": chunk_files,
        "categories": categories,
        "stats": {
            "tong_so_sp": stats.get("tong_so_sp"),
            "so_danh_muc": stats.get("so_danh_muc"),
            "het_hang": stats.get("het_hang"),
            "dang_khuyen_mai": stats.get("dang_khuyen_mai"),
            "giam_gia_tb_pct": stats.get("giam_gia_tb_pct"),
        },
    }
    (OUT_DIR / "index.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                                         encoding="utf-8")
    print(f"{len(items)} items -> {len(chunk_files)} chunks in {OUT_DIR.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
