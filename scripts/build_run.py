#!/usr/bin/env python3
"""Finalize a weekly run and RENDER the static site.

The routine (crawl → validate → index) leaves the current DB in data/db/ and the
history in data/*.csv. This script stamps the DB, extends the history, and then
generates the dashboard + per-item pages as **static HTML with the real values
baked in** — no client-side data script, no fetch. The only JS the pages load is
Chart.js + a small app.js that draws the charts from <canvas data-*> attributes.

Base week → all three index series read 100.00 (WinMart chain; BHX blank this run
because its API blocks datacenter IPs — see docs/research/POC-FINDINGS.md).

Usage:  python scripts/build_run.py [--week YYYY-MM-DD]
"""
import argparse
import csv
import datetime
import html
import json
from pathlib import Path

import lib_db

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SITE = ROOT / "site"
TPL = Path(__file__).resolve().parent / "templates"


# ---------- formatting helpers (Vietnamese conventions) ----------

def esc(s) -> str:
    return html.escape(str(s if s is not None else ""))


def vnd(n) -> str:
    return f"{int(round(n)):,}".replace(",", ".") if n is not None else "–"


def idx(v) -> str:
    return f"{v:.1f}".replace(".", ",") if v is not None else "–"


def pct(x) -> str:
    return (f"{x:+.1f}".replace(".", ",")) + "%"


def read_csv(p: Path):
    return list(csv.DictReader(p.open())) if p.exists() else []


def jarr(a) -> str:
    return json.dumps(a, ensure_ascii=False)


# ---------- HTML fragment renderers ----------

def delta_html(v) -> str:
    if v is None:
        return '<span class="delta flat">mốc gốc</span>'
    cls = "up" if v > 0.05 else "down" if v < -0.05 else "flat"
    arrow = "▲" if v > 0.05 else "▼" if v < -0.05 else "–"
    return f'<span class="delta {cls}">{arrow} {esc(pct(v))}</span>'


def movers_html(arr, cls, base_week) -> str:
    if not arr:
        msg = "Tuần đầu — chưa có thay đổi để so sánh" if base_week else "Chưa có dữ liệu"
        return f'<li class="empty">{msg}</li>'
    out = []
    for m in arr:
        arrow = "▲ " if cls == "up" else "▼ "
        out.append(f'<li><span class="nm">{esc(m["ten_chuan"])}</span>'
                   f'<span class="chip {cls}">{arrow}{esc(pct(m["pct"]))}</span></li>')
    return "".join(out)


def product_card(p) -> str:
    if p.get("hinh_anh"):
        thumb = f'<img class="thumb" src="{esc(p["hinh_anh"])}" alt="{esc(p["ten_chuan"])}" loading="lazy">'
    else:
        thumb = '<div class="thumb ph">🛒</div>'
    price = vnd(p.get("don_gia_chuan")) + "đ"
    return (f'<a class="card pcard" href="items/{esc(p["id"])}.html">'
            f'{thumb}'
            f'<div class="pn">{esc(p["ten_chuan"])}</div>'
            f'<div class="pg">{esc(p["nhom"])}</div>'
            f'<div class="pp"><span class="amt">{price}</span>'
            f'<span class="unit"> /{esc(p["don_vi_chuan"])}</span></div></a>')


def chain_card(chain, c, don_vi_chuan, ten_chuan) -> str:
    dot = {"bhx": "#199e70", "winmart": "#e66767"}[chain]
    label = {"bhx": "Bách Hóa Xanh", "winmart": "WinMart"}[chain]
    head = (f'<div class="chain-name"><span class="dot" style="background:{dot}"></span>'
            f'{label}</div>')
    if not c or c.get("trang_thai") == "out_of_stock" or not c.get("ten_hien_thi"):
        msg = "Chưa lấy được (nguồn tạm chặn)" if chain == "bhx" else "Không có tại cửa hàng"
        return (f'<div class="card chain-card"><div class="prod-img ph">🛒</div>'
                f'<div class="chain-body">{head}<p class="empty">{msg}</p></div></div>')
    if c.get("hinh_anh"):
        img = f'<img class="prod-img" src="{esc(c["hinh_anh"])}" alt="{esc(c["ten_hien_thi"])}" loading="lazy">'
    else:
        img = '<div class="prod-img ph">🛒</div>'
    rows = [f'<div class="disp-name">{esc(c["ten_hien_thi"])}</div>']
    if c.get("thuong_hieu"):
        rows.append(f'<div class="meta-row">Thương hiệu: {esc(c["thuong_hieu"])}</div>')
    if c.get("danh_muc"):
        rows.append(f'<div class="meta-row">Danh mục: {esc(c["danh_muc"])}</div>')
    pay = c.get("gia_khuyen_mai") if c.get("gia_khuyen_mai") is not None else c.get("gia_niem_yet")
    price = f'<span class="price-now">{vnd(pay)}đ</span>'
    if c.get("gia_khuyen_mai") is not None and c.get("gia_niem_yet") not in (None, c.get("gia_khuyen_mai")):
        price += f'<span class="price-old">{vnd(c["gia_niem_yet"])}đ</span>'
    st = c.get("trang_thai", "in_stock")
    badge_cls = "in" if st == "in_stock" else "carry" if st == "carry_forward" else "out"
    badge_txt = "Còn hàng" if st == "in_stock" else "Giữ giá cũ" if st == "carry_forward" else "Hết hàng"
    rows.append(f'<div class="price-block">{price}<span class="badge {badge_cls}">{badge_txt}</span></div>')
    if c.get("don_gia_chuan") is not None:
        rows.append(f'<div class="unitprice">Đơn giá chuẩn: {vnd(c["don_gia_chuan"])}đ/{esc(don_vi_chuan)}</div>')
    if c.get("url"):
        rows.append(f'<div class="store-line"><a href="{esc(c["url"])}" target="_blank" '
                    f'rel="noopener">Xem trên web ↗</a></div>')
    return (f'<div class="card chain-card">{img}'
            f'<div class="chain-body">{head}{"".join(rows)}</div></div>')


def fill(template: str, mapping: dict) -> str:
    for k, v in mapping.items():
        template = template.replace("{{" + k + "}}", v)
    return template


# ---------- main ----------

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

    # --- DB stamp (current-state) ---
    lib_db.save_products(db, updated=week)
    stores = lib_db.load_stores()
    stores["updated"] = week
    (DATA / "db" / "stores.json").write_text(
        json.dumps(stores, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lib_db.mark_run(week, captured)

    # --- history (the only time-indexed data) ---
    (DATA / "items").mkdir(parents=True, exist_ok=True)
    for it in matched:
        p = DATA / "items" / f"{it['id']}.csv"
        rows = read_csv(p)
        wm = it["chains"]["winmart"]["don_gia_chuan"]
        if not any(r["date"] == week for r in rows):
            new = not p.exists()
            with p.open("a", newline="") as f:
                w = csv.writer(f)
                if new:
                    w.writerow(["date", "bhx_don_gia_chuan", "winmart_don_gia_chuan"])
                w.writerow([week, "", wm])

    ih = DATA / "index-history.csv"
    if not any(r["date"] == week for r in read_csv(ih)):
        with ih.open("a", newline="") as f:
            csv.writer(f).writerow([week, "100.00", "", "100.00"])
    ih_all = read_csv(ih)
    first_week = len(ih_all) <= 1

    # top movers (week-over-week overall) — none on the first week
    risers, fallers = [], []
    if not first_week:
        prev_date = ih_all[-2]["date"]
        names = {it["id"]: it["ten_chuan"] for it in items}
        changes = []
        for it in matched:
            rows = read_csv(DATA / "items" / f"{it['id']}.csv")
            cur = {r["date"]: r["winmart_don_gia_chuan"] for r in rows}
            a, b = cur.get(prev_date), cur.get(week)
            if a and b:
                changes.append({"id": it["id"], "ten_chuan": names[it["id"]],
                                "pct": round(100.0 * (float(b) - float(a)) / float(a), 1)})
        changes.sort(key=lambda c: c["pct"])
        fallers = [dict(c, direction="down") for c in changes[:5] if c["pct"] < 0]
        risers = [dict(c, direction="up") for c in reversed(changes[-5:]) if c["pct"] > 0]
    (DATA / "top-movers.json").write_text(
        json.dumps({"week": week, "risers": risers, "fallers": fallers}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")

    note = (f"Đây là tuần đầu tiên nên chỉ số được đặt ở mốc 100 để làm gốc so sánh. "
            f"Tuần này ghi nhận giá của {len(matched)} mặt hàng tại WinMart; "
            f"Bách Hóa Xanh tạm thời chưa lấy được nên chỉ số dùng dữ liệu WinMart. "
            f"Từ tuần sau sẽ có thay đổi giá để theo dõi.") if first_week else \
        (f"Tuần này theo dõi {len(matched)} mặt hàng tại WinMart. "
         f"Xem chi tiết từng mặt hàng trong rổ hàng bên dưới.")

    vn_date = f"{week[8:10]}/{week[5:7]}/{week[0:4]}"
    labels = [r["date"][8:10] + "/" + r["date"][5:7] for r in ih_all]
    ser = {"chung": [float(r["index_chung"]) if r["index_chung"] else None for r in ih_all],
           "bhx": [float(r["index_bhx"]) if r["index_bhx"] else None for r in ih_all],
           "winmart": [float(r["index_winmart"]) if r["index_winmart"] else None for r in ih_all]}
    last = lambda a: a[-1] if a else None

    # --- render dashboard ---
    table_rows = "".join(
        f'<tr><td style="text-align:left">{esc(lb)}</td><td>{idx(ser["chung"][i])}</td>'
        f'<td>{idx(ser["bhx"][i])}</td><td>{idx(ser["winmart"][i])}</td></tr>'
        for i, lb in enumerate(labels))

    def wm_view(it):
        c = it["chains"]["winmart"]
        return {"id": it["id"], "ten_chuan": it["ten_chuan"], "nhom": it["nhom"],
                "don_vi_chuan": it["don_vi_chuan"], "hinh_anh": c.get("hinh_anh"),
                "don_gia_chuan": c.get("don_gia_chuan")}

    grid = "".join(product_card(wm_view(it)) for it in matched)
    compare = (f"Tuần đầu: đã lấy giá {len(matched)} mặt hàng ở WinMart. "
               f"Bách Hóa Xanh sẽ bổ sung khi có đường lấy dữ liệu ổn định." if first_week
               else f"Đang theo dõi {len(matched)} mặt hàng tại WinMart.")

    index_html = fill((TPL / "index.tmpl.html").read_text(), {
        "V_CHUNG": idx(last(ser["chung"])), "D_CHUNG": delta_html(None),
        "V_BHX": idx(last(ser["bhx"])), "D_BHX": delta_html(None),
        "V_WINMART": idx(last(ser["winmart"])), "D_WINMART": delta_html(None),
        "CHART_LABELS": esc(jarr(labels)), "CHART_CHUNG": esc(jarr(ser["chung"])),
        "CHART_BHX": esc(jarr(ser["bhx"])), "CHART_WINMART": esc(jarr(ser["winmart"])),
        "TABLE_ROWS": table_rows,
        "RISERS": movers_html(risers, "up", first_week),
        "FALLERS": movers_html(fallers, "down", first_week),
        "COMPARE": esc(compare), "NOTE": esc(note), "NOTE_DATE": f"Ghi nhận ngày {vn_date}",
        "UPDATED": vn_date, "PROD_COUNT": f"{len(matched)} mặt hàng · WinMart",
        "PRODUCT_GRID": grid,
    })
    (SITE / "index.html").write_text(index_html, encoding="utf-8")

    # --- render per-item pages ---
    items_dir = SITE / "items"
    items_dir.mkdir(exist_ok=True)
    item_tpl = (TPL / "item.tmpl.html").read_text()
    for it in matched:
        rows = read_csv(DATA / "items" / f"{it['id']}.csv")
        ilabels = [r["date"][8:10] + "/" + r["date"][5:7] for r in rows]
        ibhx = [float(r["bhx_don_gia_chuan"]) if r["bhx_don_gia_chuan"] else None for r in rows]
        iwm = [float(r["winmart_don_gia_chuan"]) if r["winmart_don_gia_chuan"] else None for r in rows]
        trs = "".join(
            f'<tr><td style="text-align:left">{esc(lb)}</td>'
            f'<td>{vnd(ibhx[i]) if ibhx[i] is not None else "–"}</td>'
            f'<td>{vnd(iwm[i]) if iwm[i] is not None else "–"}</td></tr>'
            for i, lb in enumerate(ilabels))
        chains = (chain_card("bhx", it["chains"].get("bhx"), it["don_vi_chuan"], it["ten_chuan"])
                  + chain_card("winmart", it["chains"].get("winmart"), it["don_vi_chuan"], it["ten_chuan"]))
        page = fill(item_tpl, {
            "TITLE": esc(it["ten_chuan"]), "GROUP": esc(it["nhom"]),
            "UNIT_HINT": f'đơn giá theo đ/{esc(it["don_vi_chuan"])}',
            "CHAINS": chains,
            "CHART_LABELS": esc(jarr(ilabels)), "CHART_BHX": esc(jarr(ibhx)),
            "CHART_WINMART": esc(jarr(iwm)), "UNIT": esc(it["don_vi_chuan"]),
            "TABLE_ROWS": trs,
        })
        (items_dir / f"{it['id']}.html").write_text(page, encoding="utf-8")

    # run log
    with (DATA / "run-log.md").open("a") as f:
        f.write(f"\n## {week}  (captured {captured})\n"
                f"- WinMart: ok — {len(matched)}/{len(items)} SKU\n"
                f"- BHX: blocked (apibhx.tgdd.vn resets datacenter IP) — 0/{len(items)}\n"
                f"- Index: chung 100.00 · bhx — · winmart 100.00"
                f"{' (base week)' if first_week else ''}\n")

    print(f"run {week}: {len(matched)}/{len(items)} WinMart SKUs; first_week={first_week}; "
          f"rendered site/index.html + {len(matched)} item pages")


if __name__ == "__main__":
    main()
