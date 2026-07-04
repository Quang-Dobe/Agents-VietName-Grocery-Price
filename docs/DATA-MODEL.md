# Data model — DB (current) vs History (time series)

The project keeps **two kinds of data**, deliberately separated. The full field
shapes are in `CLAUDE.md`; this page explains *why* and *what goes where*.

## 1. DB — current state (overwritten every run, never dated)

A small file-based "database" holding the **latest** value of everything. It is
rewritten in place each week — we never keep dated copies of it.

```
data/db/products.json   product catalog: rich details + CURRENT price per SKU × chain
data/db/stores.json     the pinned BHX & WinMart store (id, name, address, area)
data/db/meta.json       { last_run_week, captured_at }  ← idempotency marker
```

`products.json` is the source for the **product detail pages** (image, brand,
category, store, list/promo price, stock). Because it is current-only, the file
stays small and there is no per-date price stored here — matching the requirement
"don't save the current price by date/time".

**Why JSON files, not a server or SQLite?** The dashboard is a static GitHub Pages
site with no backend; client-side JS can `fetch()` JSON directly. A DB server is
off-architecture, and SQLite would need a heavy WASM reader in the browser. JSON is
the right "DB" here. (If you later want offline SQL analysis, we can additionally
emit a `data/db/products.sqlite` — say the word.)

## 2. History — the only time-indexed data (for dashboard analysis)

Compact time series, appended one row per week. This is the *only* place dates
live, and it exists purely to draw the charts.

```
data/index-history.csv   date,index_chung,index_bhx,index_winmart
data/items/<id>.csv      date,bhx_don_gia_chuan,winmart_don_gia_chuan
```

No dated full-price snapshot is kept. Everything the pipeline needs it derives from
these two sources plus the current DB:

| Need | Source |
|---|---|
| This week's price | `data/db/products.json` (current) |
| Last week's price (jump guard, % change) | last row of `data/items/<id>.csv` |
| Base-week price (index relative) | first row of `data/items/<id>.csv` |
| Index over time (chart) | `data/index-history.csv` |

## How a weekly run touches each store

```
crawler-bhx ‖ crawler-winmart
   └─ fetch details + current price  → write chain's side of data/db/products.json
                                      → write data/db/stores.json (store metadata)
validator
   └─ compare products.json vs last row of items CSVs → fix products.json (carry-forward, drops)
index-calculator
   └─ read products.json (now) + items CSVs (base) → append index-history.csv + items/<id>.csv
site-builder
   └─ read products.json (details) + history CSVs (charts) → rebuild site
   └─ write data/db/meta.json { last_run_week, captured_at }
```

The dated `data/prices/<date>.json` snapshot from the earlier draft is **removed** —
the DB holds current state, the CSVs hold history, and nothing needs a third copy.
