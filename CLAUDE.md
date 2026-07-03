# CLAUDE.md — project rules for `vn-grocery-price-index`

Single source of truth for every subagent. If a rule and an agent prompt
disagree, this file wins. Keep it short and current.

**What this project is:** a weekly mini-CPI over a fixed ~40-SKU grocery basket,
crawled from Bách Hóa Xanh and WinMart online, published as a dark-theme static
site on GitHub Pages. No Claude API calls — the routine writes its own commentary.
See `docs/PLAN.md` for the full plan.

---

## Golden rules

1. **API over HTML.** Always use the internal JSON APIs (§API map). Only parse
   HTML if the API fails and you have logged why.
2. **One pinned store per chain** (§Store IDs). Never change a store ID without
   adding a note to `data/substitutions-log.md` — changing store breaks the index.
3. **Be polite.** ≤ 1 request / 2–3 s per host. Realistic desktop User-Agent.
   Stop and log if you see repeated 403/429; do not hammer.
4. **Never invent prices.** If a SKU can't be read, mark it `out_of_stock` and
   follow carry-forward. A missing price is a logged gap, never a guess.
5. **Every anomaly is logged, not silently dropped.** `validator` writes its
   reasoning to the run log.
6. **Idempotent weekly runs.** If `data/prices/<this-week-saturday>.json` already
   exists, exit early (the Sunday safety run relies on this).

---

## Data schema

### `basket.json` item
```json
{
  "id": "gao-st25-5kg",
  "ten_chuan": "Gạo ST25 túi 5kg",
  "nhom": "Gạo & lương thực",
  "don_vi_chuan": "kg",
  "trong_so": 0.05,
  "urls": { "bhx": "https://www.bachhoaxanh.com/...", "winmart": "https://winmart.vn/..." },
  "quy_cach": { "bhx": "5kg", "winmart": "5kg" },
  "quy_doi": { "bhx": 5, "winmart": 5 }
}
```
- `don_vi_chuan` — the unit the index compares in (`kg`, `lít`, `quả`, `cái`).
- `trong_so` — SKU weight; all 40 sum to **1.0**.
- `quy_doi` — how many `don_vi_chuan` units are in one pack, per chain (used to get
  đơn giá chuẩn when pack sizes differ between chains).

### `data/prices/<YYYY-MM-DD>.json` (one snapshot per week)
```json
{
  "week": "2026-07-04",
  "captured_at": "2026-07-04T01:30:00+07:00",
  "store": { "bhx": "2546", "winmart": "1535/1998" },
  "items": [
    {
      "id": "gao-st25-5kg",
      "bhx":     { "gia_niem_yet": 185000, "gia_khuyen_mai": 175000, "don_gia_chuan": 35000, "trang_thai": "in_stock",     "nguon": "api" },
      "winmart": { "gia_niem_yet": 189000, "gia_khuyen_mai": null,   "don_gia_chuan": 37800, "trang_thai": "in_stock",     "nguon": "api" }
    }
  ]
}
```
- `gia_niem_yet` = list price; `gia_khuyen_mai` = promo (null if none).
- **`don_gia_chuan`** = price a shopper pays, per `don_vi_chuan`:
  `(gia_khuyen_mai ?? gia_niem_yet) / quy_doi[chain]`. This is what the index uses.
- `trang_thai` ∈ `in_stock` | `out_of_stock` | `carry_forward`.
- All prices are integers in **VND**.

### `data/index-history.csv`
```
date,index_chung,index_bhx,index_winmart
2026-07-04,100.00,100.00,100.00
```

### `data/items/<id>.csv`
```
date,bhx_don_gia_chuan,winmart_don_gia_chuan
2026-07-04,35000,37800
```

---

## Index formula (Laspeyres, base 100 at week 1)

For SKU *i*, chain *c*: relative `R_i,c = don_gia_chuan_now / don_gia_chuan_base`.
- **Per chain:** `index_c = 100 × Σ_i (w_i × R_i,c) / Σ_i w_i` over SKUs available
  that week on chain *c* (renormalize weights over the available set).
- **Overall (`index_chung`):** first average the two chains per SKU
  `R_i = mean(R_i,bhx, R_i,winmart)` (use whichever chains are available), then
  `index_chung = 100 × Σ_i (w_i × R_i) / Σ_i w_i`.
- **Base week** = the first snapshot; all three series read exactly `100.00` there.
- **Substitution week:** apply the chain-link factor so the level does not jump
  (see `docs/PLAN.md` §5).

---

## Validation rules (`validator`)

- **Jump guard:** if `don_gia_chuan` moves **> 50 %** vs last week for a SKU/chain,
  flag as suspected parse error. Default action: **drop that reading** (carry
  forward instead) and log the raw value + reason. Keep it only if the crawler can
  show the live promo that justifies it.
- **Sanity band:** reject non-positive prices, prices off the item's historical
  median by > 10× (unit/parse bug), and unit-price mismatches between chains > 5×
  (likely a `quy_doi` error — fix `basket.json`, don't discard the SKU).
- **Coverage:** if a chain returns < 70 % of basket SKUs, log a source warning; if
  < 40 %, treat the chain as failed for the week (index uses the other chain).
- **Carry-forward:** `out_of_stock` → reuse last `don_gia_chuan`, mark
  `carry_forward`, **max 2 consecutive weeks**, then exclude from the period.

---

## API map (verified — see `docs/research/POC-FINDINGS.md`)

### Bách Hóa Xanh — `https://apibhx.tgdd.vn`
Headers: `Authorization: Bearer <token>`, `deviceid: <uuid>`,
`xapikey: bhx-api-core-2022`, `origin: https://www.bachhoaxanh.com`,
`referer: https://www.bachhoaxanh.com/`, realistic `user-agent`.
- Token is **short-lived** — mint it per run with Playwright
  (`scripts/bhx_token.py`): open `www.bachhoaxanh.com`, intercept the
  `authorization` header off a `Menu/GetMenuV2` / `Location/...` request; read
  `deviceid` from cookie `ck_bhx_us_log` (`.did`) or generate a UUID.
- Category products: `GET /Category/V2/GetCate?provinceId=&wardId=&districtId=&storeId=&categoryUrl=<slug>&isMobile=true&isV2=true&pageSize=300`
- Paged: `POST /Category/AjaxProduct` `{provinceId,wardId,districtId,storeId,CategoryId,PageIndex,PageSize}`
- Products at `data.products[]`. **Field map (confirm on first live dump):**
  name→`name`, unit→`unit`, net size→`netUnitValue`, list price→`sysPrice`,
  promo/current price→`price`, discount→`discountPercent`, stock→stock flag.
  ⚠️ If a live product's fields differ, **fix them here** — this is the only place.

### WinMart — `https://api-crownx.winmart.vn`
Headers: browser UA, `origin: https://winmart.vn`, `referer: https://winmart.vn/`.
- Category products: `GET /it/api/web/v3/item/category?orderByDesc=true&pageNumber=1&pageSize=100&slug=<cat-slug>&storeCode=<code>&storeGroupCode=<group>`
- **Field map (confirm on first live dump):** name→`name`, list price→`price`,
  promo/current→`salePrice`, unit→`uom`/`uomName`, product slug→`seoName`.

---

## Store IDs (pin at PoC, then never change silently)

| Chain | Fields | Value | Set |
|---|---|---|---|
| BHX | `provinceId`, `storeId` | _TBD at PoC_ (central HCMC store) | ⬜ |
| WinMart | `storeCode`, `storeGroupCode` | _TBD at PoC_ (central HCMC store) | ⬜ |

---

## Allowed domains (cloud environment)

Mirror of `config/allowed-domains.txt`:
`bachhoaxanh.com`, `www.bachhoaxanh.com`, `apibhx.tgdd.vn`, `winmart.vn`,
`www.winmart.vn`, `api-crownx.winmart.vn`. Add any new API host you discover here
**and** in `config/allowed-domains.txt`.

---

## Writing style for site copy (the agent's weekly note & UI text)

Vietnamese, **short and plain**. Say what changed and why it matters to a shopper.
No jargon, no hype. 2–4 sentences for the weekly note. Numbers rounded (e.g.
"tăng 1,2%"). See `docs/UI-DESIGN.md` for the full copy + visual style.
