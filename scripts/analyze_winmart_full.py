#!/usr/bin/env python3
"""Deterministic stats over the full WinMart catalog (data/full/winmart-catalog.json).

Pure formula, no LLM judgment: per-category counts/price range/promo rate, and an
overall summary. Written as its own script (not computed ad hoc) so the numbers
are reproducible run to run.

Usage:  python scripts/analyze_winmart_full.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "data" / "full" / "winmart-catalog.json"
OUT = ROOT / "data" / "full" / "winmart-catalog-stats.json"


def mean(xs):
    xs = list(xs)
    return round(sum(xs) / len(xs)) if xs else None


def analyze(items: list) -> dict:
    by_cat = {}
    for it in items:
        cat = it.get("danh_muc") or "Khác"
        by_cat.setdefault(cat, []).append(it)

    categories = []
    for cat, its in sorted(by_cat.items(), key=lambda kv: -len(kv[1])):
        prices = [it["gia_ban"] for it in its if it.get("gia_ban")]
        promo = [it for it in its if it.get("gia_khuyen_mai")]
        in_stock = [it for it in its if it.get("trang_thai") == "in_stock"]
        categories.append({
            "danh_muc": cat,
            "so_luong": len(its),
            "con_hang": len(in_stock),
            "gia_tb": mean(prices),
            "gia_min": min(prices) if prices else None,
            "gia_max": max(prices) if prices else None,
            "so_khuyen_mai": len(promo),
            "giam_gia_tb_pct": (round(sum(it["giam_gia_pct"] for it in promo) / len(promo), 1)
                                if promo else None),
        })

    total = len(items)
    out_of_stock = sum(1 for it in items if it.get("trang_thai") == "out_of_stock")
    promo_all = [it for it in items if it.get("gia_khuyen_mai")]
    top_discount = sorted(
        (it for it in items if it.get("giam_gia_pct")),
        key=lambda it: -it["giam_gia_pct"],
    )[:10]

    return {
        "tong_so_sp": total,
        "so_danh_muc": len(by_cat),
        "het_hang": out_of_stock,
        "dang_khuyen_mai": len(promo_all),
        "giam_gia_tb_pct": (round(sum(it["giam_gia_pct"] for it in promo_all) / len(promo_all), 1)
                            if promo_all else None),
        "danh_muc": categories,
        "top_giam_gia": [
            {"ten": it["ten"], "danh_muc": it["danh_muc"], "giam_gia_pct": it["giam_gia_pct"],
             "gia_niem_yet": it["gia_niem_yet"], "gia_ban": it["gia_ban"]}
            for it in top_discount
        ],
    }


def main() -> None:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    stats = analyze(catalog.get("items") or [])
    stats["updated"] = catalog.get("updated")
    OUT.write_text(json.dumps(stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{stats['tong_so_sp']} products / {stats['so_danh_muc']} categories -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
