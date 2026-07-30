# Run log

One entry per weekly run. Written by the routine (see `ROUTINE_PROMPT.md`).

Format:
```
## <YYYY-MM-DD>  (captured <ISO time>)
- BHX: <ok|failed> — <n>/<40> SKU
- WinMart: <ok|failed> — <n>/<40> SKU
- Substitutions: <n>  (see substitutions-log.md)
- Anomalies dropped: <n>
- Index: chung <v> · bhx <v> · winmart <v>
- Notes: <...>
```

<!-- runs appended below -->

## 2026-07-04  (captured 2026-07-04T06:00:00+07:00)
- WinMart: ok — 35/40 SKU
- BHX: blocked from cloud (apibhx.tgdd.vn resets datacenter IP); run locally — see docs/LOCAL-RUN.md
- Index: chung 100.00 · bhx — · winmart 100.00 (base week)

## 2026-07-08  (captured 2026-07-08T06:00:00+07:00)
- WinMart: ok — 34/40 SKU matched by crawler; 30/40 counted as this week's reading
- BHX: blocked (apibhx.tgdd.vn resets datacenter IP) — 0/40
- Anomalies dropped: 4 (jump guard, >50% vs last week — crawler matched a different
  specific product than last week, not a real price move; carried forward last
  week's `don_gia_chuan` and marked `carry_forward` instead of publishing):
  - tom-the-500g: raw 665.000đ (matched "Tôm thẻ nõn HDC hộp 200g") vs last week
    299.900đ ("HDC Tôm thẻ hấp ĐL size 40-60con/kg") → +121.7%, kept 299.900đ
  - tao-my-1kg: raw 135.000đ ("Táo Gala New túi 1Kg") vs last week 49.000đ
    ("WMNK Táo Gala Nam Phi size nhỏ") → +175.5%, kept 49.000đ
  - giay-ve-sinh-loc10: raw 10.900đ ("Giấy vệ sinh Fairy cao cấp 10 cuộn 4 lớp")
    vs last week 6.500đ ("Giấy vệ sinh Elene hồng 3 lớp 10 cuộn") → +67.7%, kept
    6.500đ
  - nuoc-rua-chen-sunlight-750g: raw 94.267đ ("Nước rửa chén Suzy hương bạc hà
    chai 2,1kg", likely also a `net`/quy_doi mismatch) vs last week 38.400đ
    ("Nước rửa chén chanh Sunlight chai 750g") → +145.5%, kept 38.400đ
- Index: chung 100.00 · bhx — · winmart 100.00
- Notes: these 4 SKUs' `basket.json` entries could use `match.kw`/`must` hints to
  pin WinMart search to the same specific product week over week (see
  `docs/DATA-MODEL.md` match hints). `build_run.py`'s history/site step only
  includes `trang_thai: in_stock` items, so carry_forward SKUs get no history row
  this week (their item pages keep last week's data) rather than a repeated-value
  row — acceptable for one week, but worth revisiting if this keeps recurring.
  Separately: `index-history.csv` values are still a hardcoded 100.00 placeholder
  in `build_run.py` (the weighted Laspeyres formula from `CLAUDE.md` isn't wired
  up yet) — flagged for follow-up, out of scope for this weekly-data run.

## 2026-07-09  (captured 2026-07-09T06:00:00+07:00)
- WinMart: ok — 36/40 SKU
- BHX: blocked (apibhx.tgdd.vn resets datacenter IP) — 0/40
- Index: chung 100.00 · bhx — · winmart 100.00

## 2026-07-10  (captured 2026-07-10T06:00:00+07:00)
- WinMart: ok — 35/40 SKU
- BHX: blocked (apibhx.tgdd.vn resets datacenter IP) — 0/40
- Index: chung 100.00 · bhx — · winmart 100.00

## 2026-07-11  (captured 2026-07-11T06:00:00+07:00)
- WinMart: ok — 36/40 SKU
- BHX: blocked (apibhx.tgdd.vn resets datacenter IP) — 0/40
- Index: chung 100.00 · bhx — · winmart 100.00

## 2026-07-13  (captured 2026-07-13T06:00:00+07:00)
- WinMart: ok — 35/40 SKU
- BHX: blocked (apibhx.tgdd.vn resets datacenter IP) — 0/40
- Index: chung 100.00 · bhx — · winmart 100.00

## 2026-07-14  (captured 2026-07-14T06:00:00+07:00)
- WinMart: ok — 34/40 SKU
- BHX: blocked (apibhx.tgdd.vn resets datacenter IP) — 0/40
- Index: chung 100.00 · bhx — · winmart 100.00

## 2026-07-15  (captured 2026-07-15T06:00:00+07:00)
- WinMart: ok — 34/40 SKU
- BHX: blocked (apibhx.tgdd.vn resets datacenter IP) — 0/40
- Index: chung 100.00 · bhx — · winmart 100.00

## 2026-07-18  (captured 2026-07-18T06:00:00+07:00)
- WinMart: ok — 35/40 SKU
- BHX: blocked (apibhx.tgdd.vn resets datacenter IP) — 0/40
- Index: chung 100.00 · bhx — · winmart 100.00

## 2026-07-20  (captured 2026-07-20T06:00:00+07:00)
- WinMart: ok — 33/40 SKU
- BHX: blocked (apibhx.tgdd.vn resets datacenter IP) — 0/40
- Index: chung 100.00 · bhx — · winmart 100.00

## 2026-07-22  (captured 2026-07-22T06:00:00+07:00)
- WinMart: ok — 34/40 SKU
- BHX: blocked (apibhx.tgdd.vn resets datacenter IP) — 0/40
- Index: chung 100.00 · bhx — · winmart 100.00

### 2026-07-30 — bug fix note
`build_run.py` was found to hardcode the index at 100.00 every run instead of
calling `lib_index.compute_indices()` (which was defined but never invoked).
Fixed the script and retroactively recomputed `data/index-history.csv` from
the real per-item price history in `data/items/*.csv` (source of truth,
unaffected by the bug). Corrected series: 04/07=100.00, 08/07=114.35,
09/07=105.67, 10/07=106.62, 11/07=105.31, 13/07=105.39, 14/07=105.63,
15/07=106.55, 18/07=104.71, 20/07=105.99, 22/07=109.29.

While computing this week's (30/07) figure, `ca-chua-1kg`/WinMart raw don_gia_chuan
came back 66.333đ (crawler matched "Cà chua cherry đỏ 300g", a different product
than the ~27.000đ/kg item matched every prior week) → +145.7%, tripping the
jump-guard (>50%, CLAUDE.md §Validation). Applied the documented default action:
dropped the reading, carried forward 27.000đ into `products.json` and
`data/items/ca-chua-1kg.csv`, marked `carry_forward`. That's why this week's
WinMart count is 33/40 (not 34) and the item is excluded from this week's history
row / index / item page per existing carry_forward convention (see 08/07 entry
above). Final corrected index for 30/07 is below.

## 2026-07-30  (captured 2026-07-30T06:00:00+07:00)
- WinMart: ok — 33/40 SKU
- BHX: blocked (apibhx.tgdd.vn resets datacenter IP) — 0/40
- Index: chung 106.88 · bhx — · winmart 106.88
