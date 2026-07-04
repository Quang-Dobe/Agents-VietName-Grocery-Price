#!/usr/bin/env python3
"""Finalize a weekly run: stamp the DB, extend the history, and publish the site's
data files (site/data/*) that the static pages fetch.

Base week → all three index series read 100.00 (WinMart chain; BHX blank this run
because its API blocks datacenter IPs — see docs/research/POC-FINDINGS.md).

Usage:  python scripts/build_run.py [--week YYYY-MM-DD]
"""
import argparse
import csv
import datetime
import json
import shutil
from pathlib import Path

import lib_db

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SITE_DATA = ROOT / "site" / "data"


def read_history(csv_path: Path):
    if not csv_path.exists():
        return []
    with csv_path.open() as f:
        return list(csv.DictReader(f))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--week", default=datetime.date.today().isoformat())
    args = ap.parse_args()
    week = args.week
    captured = f"{week}T06:00:00+07:00"

    db = lib_db.load_products()
    items = db.get("items", [])
    matched = [it for it in items
               if (it["chains"].get("winmart") or {}).get("trang_thai") == "in_stock"]

    # --- stamp the DB (current-state) ---
    lib_db.save_products(db, updated=week)
    stores = lib_db.load_stores()
    stores["updated"] = week
    (DATA / "db" / "stores.json").write_text(
        json.dumps(stores, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lib_db.mark_run(week, captured)

    # --- extend history (the only time-indexed data) ---
    # per-item CSVs: base week rows (bhx blank — chain blocked this run)
    (DATA / "items").mkdir(parents=True, exist_ok=True)
    for it in matched:
        p = DATA / "items" / f"{it['id']}.csv"
        rows = read_history(p)
        wm = it["chains"]["winmart"]["don_gia_chuan"]
        if not any(r["date"] == week for r in rows):
            new = not p.exists()
            with p.open("a", newline="") as f:
                w = csv.writer(f)
                if new:
                    w.writerow(["date", "bhx_don_gia_chuan", "winmart_don_gia_chuan"])
                w.writerow([week, "", wm])

    # index-history.csv (base week → 100 on the available WinMart chain)
    ih = DATA / "index-history.csv"
    ih_rows = read_history(ih)
    base_week = not any(r["date"] == week for r in ih_rows)
    if base_week:
        with ih.open("a", newline="") as f:
            csv.writer(f).writerow([week, "100.00", "", "100.00"])

    # top-movers: none on the base week
    (DATA / "top-movers.json").write_text(
        json.dumps({"week": week, "risers": [], "fallers": []}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")

    # --- the agent's weekly note (base week, honest about BHX) ---
    note = (f"Đây là tuần đầu tiên nên chỉ số được đặt ở mốc 100 để làm gốc so sánh. "
            f"Tuần này ghi nhận giá của {len(matched)} mặt hàng tại WinMart; "
            f"Bách Hóa Xanh tạm thời chưa lấy được nên chỉ số dùng dữ liệu WinMart. "
            f"Từ tuần sau sẽ có thay đổi giá để theo dõi.")

    # --- publish site data (served under site/) ---
    SITE_DATA.mkdir(parents=True, exist_ok=True)
    (SITE_DATA / "items").mkdir(exist_ok=True)
    shutil.copyfile(DATA / "db" / "products.json", SITE_DATA / "products.json")

    ih_all = read_history(ih)
    labels = [r["date"][5:].replace("-", "/") for r in ih_all]  # MM/DD
    series = {
        "labels": labels,
        "chung": [float(r["index_chung"]) if r["index_chung"] else None for r in ih_all],
        "bhx": [float(r["index_bhx"]) if r["index_bhx"] else None for r in ih_all],
        "winmart": [float(r["index_winmart"]) if r["index_winmart"] else None for r in ih_all],
    }

    def wm_view(it):
        c = it["chains"]["winmart"]
        pay = c.get("gia_khuyen_mai") or c.get("gia_niem_yet")
        return {"id": it["id"], "ten_chuan": it["ten_chuan"], "nhom": it["nhom"],
                "don_vi_chuan": it["don_vi_chuan"], "ten_hien_thi": c.get("ten_hien_thi"),
                "hinh_anh": c.get("hinh_anh"), "gia": pay,
                "don_gia_chuan": c.get("don_gia_chuan"), "url": c.get("url")}

    dashboard = {
        "updated": _vn_date(week), "week": week, "base_week": len(ih_all) <= 1,
        "index": {"chung": 100.0, "bhx": None, "winmart": 100.0},
        "deltas": {"chung": None, "bhx": None, "winmart": None},
        "series": series,
        "risers": [], "fallers": [],
        "compare": (f"Tuần đầu: đã lấy giá {len(matched)} mặt hàng ở WinMart. "
                    f"Bách Hóa Xanh sẽ bổ sung khi có đường lấy dữ liệu ổn định."),
        "note": note, "note_date": f"Ghi nhận ngày {_vn_date(week)}",
        "coverage": {"winmart": len(matched), "total": len(items)},
        "products": [wm_view(it) for it in matched],
    }
    (SITE_DATA / "dashboard.json").write_text(
        json.dumps(dashboard, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # per-item history for the detail pages + an items map for the JS bundle
    items_map = {}
    for it in matched:
        rows = read_history(DATA / "items" / f"{it['id']}.csv")
        hist = {
            "labels": [r["date"][5:].replace("-", "/") for r in rows],
            "bhx": [float(r["bhx_don_gia_chuan"]) if r["bhx_don_gia_chuan"] else None for r in rows],
            "winmart": [float(r["winmart_don_gia_chuan"]) if r["winmart_don_gia_chuan"] else None for r in rows],
        }
        (SITE_DATA / "items" / f"{it['id']}.json").write_text(
            json.dumps(hist, ensure_ascii=False) + "\n", encoding="utf-8")
        items_map[it["id"]] = {"id": it["id"], "ten_chuan": it["ten_chuan"], "nhom": it["nhom"],
                               "don_vi_chuan": it["don_vi_chuan"], "chains": it["chains"], "history": hist}

    # JS bundles: loaded via <script src>, so the UI shows real data BOTH on the
    # live site and when index.html is opened as a local file (fetch() can't do that).
    (SITE_DATA / "dashboard.js").write_text(
        "window.GIACHO = " + json.dumps(dashboard, ensure_ascii=False) + ";\n", encoding="utf-8")
    (SITE_DATA / "items.js").write_text(
        "window.GIACHO_ITEMS = " + json.dumps(items_map, ensure_ascii=False) + ";\n", encoding="utf-8")

    # run log
    with (DATA / "run-log.md").open("a") as f:
        f.write(f"\n## {week}  (captured {captured})\n"
                f"- WinMart: ok — {len(matched)}/{len(items)} SKU\n"
                f"- BHX: blocked (apibhx.tgdd.vn resets datacenter IP) — 0/{len(items)}\n"
                f"- Index: chung 100.00 · bhx — · winmart 100.00 (base week)\n")

    print(f"run {week}: {len(matched)}/{len(items)} WinMart SKUs; base_week={base_week}; "
          f"published site/data/ (dashboard + {len(matched)} item files)")


def _vn_date(iso: str) -> str:
    y, m, d = iso.split("-")
    return f"{d}/{m}/{y}"


if __name__ == "__main__":
    main()
