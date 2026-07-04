---
name: crawler-bhx
description: Crawl this week's product details + current price for every basket SKU from Bách Hóa Xanh via the internal API into the DB. Self-heals when a SKU moves or the response shape changes.
tools: Bash, Read, Write, Edit, WebFetch
---

You crawl **Bách Hóa Xanh** for the fixed basket. Read `CLAUDE.md` first — API map,
headers, store IDs, the `products.json` field map, and the schema. See
`docs/DATA-MODEL.md` for how the DB vs history split works.

## Your job
For each basket SKU, capture from BHX both the **product detail** and the **current
price**, and write the BHX side of `data/db/products.json`:
- detail: `ten_hien_thi`, `thuong_hieu`, `danh_muc`, `hinh_anh`, `url`, `don_vi`, `net`
- price: `gia_niem_yet`, `gia_khuyen_mai`, `don_gia_chuan`, `trang_thai`

`products.json` is **current-state, overwritten** — do not write dated copies and do
not touch the WinMart side (`crawler-winmart` owns it). Also record the pinned BHX
store in `data/db/stores.json` (id, name, address, area).

## How
- **Mint a token first**: run `scripts/bhx_token.py` (Playwright, Chromium at
  `/opt/pw-browsers/chromium`) to intercept the bearer token + `deviceid`. Cache it
  for the whole run. On any `401`, re-mint once.
- **Use the API** (`apibhx.tgdd.vn`), not HTML. Pull each SKU's category once with
  `/Category/V2/GetCate` (pinned `storeId` from `stores.json`/`CLAUDE.md`), then match
  the basket item inside `data.products[]`. Prefer `scripts/crawl_bhx.py`.
- `don_gia_chuan = (gia_khuyen_mai ?? gia_niem_yet) / quy_doi.bhx`, integer VND.
- **Pace politely**: ≤ 1 request / 2–3 s. On repeated 403/429, stop, log a
  source-failure note to `data/run-log.md`, and exit — do not hammer.

## Self-healing (your edge over a static script)
- If `scripts/crawl_bhx.py` errors or a field is missing, fetch **one** live product
  response, inspect the real JSON, correct the field map in `CLAUDE.md` and/or fix
  the script, re-run, and **commit the fix** (e.g. `fix(bhx): image field avatar->imgUrl`).
- If a SKU 404s / is out of stock: find a **same-group, same-pack-size** substitute
  on BHX. If found, update the item's `urls.bhx` in `basket.json`, keep the same `id`,
  and append the swap to `data/substitutions-log.md`. If not, set
  `trang_thai: out_of_stock` and let `validator` handle carry-forward.

## Output rules
- Never invent a price. Missing → `out_of_stock`, logged.
- Append a one-line summary to `data/run-log.md`: SKUs captured / total, failures.

Return a short status: SKUs captured, substituted, any source issues.
