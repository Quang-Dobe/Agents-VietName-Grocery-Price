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

## 2026-07-23  (captured 2026-07-23T06:00:00+07:00)
- WinMart: ok — 33/40 SKU
- BHX: blocked (apibhx.tgdd.vn resets datacenter IP) — 0/40
- Index: chung 100.00 · bhx — · winmart 100.00

## 2026-08-02  (captured 2026-08-02T06:00:00+07:00)
- WinMart: ok — 33/40 SKU
- BHX: blocked (apibhx.tgdd.vn resets datacenter IP) — 0/40
- Index: chung 100.00 · bhx — · winmart 100.00

## 2026-08-03  (captured 2026-08-03T06:00:00+07:00)
- WinMart: ok — 33/40 SKU
- BHX: blocked (apibhx.tgdd.vn resets datacenter IP) — 0/40
- Index: chung 100.00 · bhx — · winmart 100.00

## 2026-08-08  (captured 2026-08-08T06:00:00+07:00)
- WinMart: ok — 31/40 SKU (32 matched by the crawler; 1 dropped by validator, see below)
- BHX: blocked (apibhx.tgdd.vn resets datacenter IP) — 0/40
- Index: chung 104.78 · bhx — · winmart 104.78
- Validator: `ga-ta-nguyen-con-1kg` (Gà ta nguyên con) crawler match was "Trứng gà ta
  Ba Vì 729 Omega 3" — a carton of eggs, not a whole chicken — at score 0.50 (the
  min-score floor). Implied price move 129.900đ → 60.000đ (−53,8%), over the >50%
  jump-guard threshold. Dropped the reading and marked the SKU `out_of_stock` for
  this week (excluded from the index and item history) rather than carry-forward,
  since the matched product's identity — not just its price — is wrong.
- Bug fix: `scripts/build_run.py` computed `index_chung`/`index_winmart` as a
  hardcoded "100.00" stub every week instead of calling `lib_index.compute_indices`
  — the index has been flat since the project started despite real price moves in
  the per-item history. Fixed to use `lib_index.py` (already correct, just never
  wired in) for this week onward. Did **not** backfill past weeks' index-history.csv
  rows: recomputing them surfaced other likely bad crawler matches in the historical
  per-item CSVs (e.g. `tao-my-1kg` 49.000đ→135.000đ, `nuoc-rua-chen-sunlight-750g`
  38.400đ→94.267đ, both >100% single-week jumps around 2026-07-08) that were never
  caught by a validator pass — backfilling on top of that data would launder bad
  matches into permanent history. Recommend a one-off historical validator pass
  before trusting or backfilling those older rows.
