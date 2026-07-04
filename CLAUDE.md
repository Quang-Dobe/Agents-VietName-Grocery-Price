# CLAUDE.md — project rules for `vn-grocery-price-index`

Single source of truth for every subagent. If a rule and an agent prompt
disagree, this file wins. Keep it short and current.

**What this project is:** a weekly mini-CPI over a fixed ~40-SKU grocery basket,
crawled from Bách Hóa Xanh and WinMart online, published as a dark-theme static
site on GitHub Pages. No Claude API calls — the routine writes its own commentary.
See `docs/PLAN.md` for the full plan.

**Two data stores, on purpose (see `docs/DATA-MODEL.md`):**
- **DB = current state, overwritten every run, never dated.** Rich product details
  + the current price for each SKU on each chain, plus the pinned store metadata.
  This is what the product pages read.
- **History = the only time-indexed data, kept for dashboard analysis.** Compact
  per-item and index CSVs. We do **not** keep dated full-price snapshots.

---

## Golden rules

1. **API over HTML.** Always use the internal JSON APIs (§API map). Only parse
   HTML if the API fails and you have logged why.
2. **One pinned store per chain** (§Store IDs → recorded in `data/db/stores.json`).
   Never change a store ID without adding a note to `data/substitutions-log.md` —
   changing store breaks the index.
3. **Be polite.** ≤ 1 request / 2–3 s per host. Realistic desktop User-Agent.
   Stop and log if you see repeated 403/429; do not hammer.
4. **Never invent prices.** If a SKU can't be read, mark it `out_of_stock` and
   follow carry-forward. A missing price is a logged gap, never a guess.
5. **Every anomaly is logged, not silently dropped.** `validator` writes its
   reasoning to the run log.
6. **Idempotent weekly runs.** If `data/db/meta.json` `last_run_week` == this
   week's Saturday, exit early (the Sunday safety run relies on this).
7. **DB is current-only.** Overwrite `data/db/*.json` each run — never write a
   dated copy of it. Time series belong in the history CSVs, nowhere else.

---

## Data schema

### `basket.json` item (the fixed SKU definition — version-controlled)
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
- `quy_doi` — how many `don_vi_chuan` units are in one pack, per chain.
- **`match`** (optional, WinMart matching hints — curate when the default fuzzy
  match picks a wrong product): `{ "kw": [search terms, specific→general],
  "must": [tokens a candidate MUST contain], "avoid": [phrases that disqualify],
  "head_start": true }`. `head_start` requires the product name to *lead* with the
  SKU's head noun (rejects e.g. a "Vinamilk … Cà Phê" drink for a coffee SKU). The
  crawler also searches the **deaccented** term (the API misses some accented
  queries, e.g. "đường" → nothing, "duong" → sugar).

### `data/db/products.json` — product catalog: **current details + current price** (overwritten every run)
The "database" the product pages read. Rich detail plus the latest price for each
SKU on each chain. Overwritten in place each run — **no dated copies**.
```json
{
  "updated": "2026-07-04",
  "items": [
    {
      "id": "gao-st25-5kg",
      "ten_chuan": "Gạo ST25 túi 5kg",
      "nhom": "Gạo & lương thực",
      "don_vi_chuan": "kg",
      "chains": {
        "bhx": {
          "ten_hien_thi": "Gạo ST25 Ông Cua túi 5kg",
          "thuong_hieu": "ST25 Ông Cua",
          "danh_muc": "Gạo",
          "hinh_anh": "https://cdn.tgdd.vn/.../gao-st25.jpg",
          "url": "https://www.bachhoaxanh.com/...",
          "quy_cach": "5kg", "don_vi": "túi", "net": 5,
          "gia_niem_yet": 185000, "gia_khuyen_mai": 175000, "don_gia_chuan": 35000,
          "trang_thai": "in_stock", "nguon": "api"
        },
        "winmart": {
          "ten_hien_thi": "Gạo ST25 túi 5kg",
          "thuong_hieu": "ST25", "danh_muc": "Gạo",
          "hinh_anh": "https://.../st25.jpg",
          "url": "https://winmart.vn/products/...",
          "quy_cach": "5kg", "don_vi": "túi", "net": 5,
          "gia_niem_yet": 189000, "gia_khuyen_mai": null, "don_gia_chuan": 37800,
          "trang_thai": "in_stock", "nguon": "api"
        }
      }
    }
  ]
}
```

### `data/db/stores.json` — pinned store metadata (current, overwritten)
```json
{
  "updated": "2026-07-04",
  "stores": {
    "bhx":     { "provinceId": 3,  "storeId": 2546, "ten": "BHX <đường/phường>",     "dia_chi": "...", "khu_vuc": "TP.HCM" },
    "winmart": { "storeCode": 1535, "storeGroupCode": 1998, "ten": "WinMart <...>",  "dia_chi": "...", "khu_vuc": "TP.HCM" }
  }
}
```

### `data/db/meta.json` — run marker (idempotency guard)
```json
{ "last_run_week": "2026-07-04", "captured_at": "2026-07-04T01:30:00+07:00" }
```

### History — the **only** time-indexed data (for dashboard analysis)
```
data/index-history.csv    date,index_chung,index_bhx,index_winmart
data/items/<id>.csv       date,bhx_don_gia_chuan,winmart_don_gia_chuan
```
- We do **not** store a dated full-price snapshot. To compute this week's move:
  read the current `don_gia_chuan` from `products.json` and the previous value from
  the **last row** of `data/items/<id>.csv`; the **base week** is the **first row**.

### Price fields (in `products.json.chains.<chain>`)
- `gia_niem_yet` = list price; `gia_khuyen_mai` = promo (null if none).
- **`don_gia_chuan`** = price a shopper pays, per `don_vi_chuan`:
  `(gia_khuyen_mai ?? gia_niem_yet) / quy_doi[chain]`. This is what the index uses.
- `trang_thai` ∈ `in_stock` | `out_of_stock` | `carry_forward`.
- All prices are integers in **VND**.

---

## Index formula (Laspeyres, base 100 at week 1)

For SKU *i*, chain *c*: relative `R_i,c = don_gia_chuan_now / don_gia_chuan_base`.
- **Per chain:** `index_c = 100 × Σ_i (w_i × R_i,c) / Σ_i w_i` over SKUs available
  that week on chain *c* (renormalize weights over the available set).
- **Overall (`index_chung`):** first average the two chains per SKU
  `R_i = mean(R_i,bhx, R_i,winmart)` (use whichever chains are available), then
  `index_chung = 100 × Σ_i (w_i × R_i) / Σ_i w_i`.
- `don_gia_chuan_now` comes from `products.json`; `don_gia_chuan_base` is the first
  row of `data/items/<id>.csv`.
- **Substitution week:** apply the chain-link factor so the level does not jump
  (see `docs/PLAN.md` §5).

---

## Validation rules (`validator`)

Operates on `data/db/products.json` (this week's current values) vs the last row of
each `data/items/<id>.csv` (previous week). Corrections are written back into
`products.json` before the index is computed.

- **Jump guard:** if `don_gia_chuan` moves **> 50 %** vs last week for a SKU/chain,
  flag as suspected parse error. Default action: **drop that reading** (carry
  forward the previous value into `products.json`, mark `carry_forward`) and log the
  raw value + reason. Keep it only if the crawler can show the live promo.
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
- Stores in a province: `GET /Location/V2/GetStoresByLocation?provinceId=<id>` → record chosen store in `stores.json`.
- Category products: `GET /Category/V2/GetCate?provinceId=&wardId=&districtId=&storeId=&categoryUrl=<slug>&isMobile=true&isV2=true&pageSize=300`
- Paged: `POST /Category/AjaxProduct` `{provinceId,wardId,districtId,storeId,CategoryId,PageIndex,PageSize}`
- Products at `data.products[]`.

### WinMart — `https://api-crownx.winmart.vn` ✅ LIVE-VERIFIED (works from cloud)
Headers: browser UA, `origin: https://winmart.vn`, `referer: https://winmart.vn/`.
No bearer token needed. Pinned store `storeCode=1535`, `storeGroupCode=1998`.
- Search (best for matching a specific SKU): `GET /it/api/web/v3/item/search?keyword=<kw>&storeCode=&storeGroupCode=&pageNumber=1&pageSize=20` → items at `data[]`. **Search is loosely ranked** — score candidates and reject bad hits (a "gạo ST25" search can return snacks).
- Category listing: `GET /it/api/web/v3/item/category?...&slug=<cat-slug>&storeCode=&storeGroupCode=` → items at `data.items[]`.

### BHX — ⚠️ API BLOCKED FROM CLOUD DATACENTER IP
`apibhx.tgdd.vn` **resets the TCP connection** from this environment's datacenter IP
(origin-side anti-bot, not our proxy — confirmed 2026-07-04). `www.bachhoaxanh.com`
itself returns 200, but the API host does not answer. **BHX runs via the local
fallback** (`docs/PLAN.md` §7); the cloud routine crawls WinMart only and the index
uses the WinMart chain (coverage rule) until BHX has a residential-IP path.

### Product field map → `products.json` (WinMart confirmed live; BHX to confirm on local run)
| `products.json` field | WinMart (item) — CONFIRMED | BHX (`data.products[]`) |
|---|---|---|
| `ten_hien_thi` | `name` | `name` |
| `thuong_hieu` | `brandName` | `brandName` / `brand` |
| `danh_muc` | `categoryName` / `mch3Name` | `category` / from slug |
| `hinh_anh` | `mediaUrl` | `avatar` / `imgUrl` / `images[0]` |
| `url` | `https://winmart.vn/products/<seoName>` | build from `url`/seo slug |
| `don_vi` | `uomName` | `unit` |
| `net` | `quantityPerUnit` | `netUnitValue` |
| `gia_niem_yet` | `price` | `sysPrice` |
| `gia_khuyen_mai` | `salePrice` (if < `price`) | `price` (if < sysPrice) |
| stock (`trang_thai`) | `quantity` > 0 → in_stock | stock flag |

**đơn giá chuẩn (WinMart):** `(salePrice||price) / quantityPerUnit` when `uomName`
matches `don_vi_chuan` (item priced per its own net); else fall back to basket `quy_doi`.

---

## Store IDs (pin at PoC, then never change silently → live in `data/db/stores.json`)

| Chain | Fields | Value | Set |
|---|---|---|---|
| BHX | `provinceId`, `storeId` | _TBD at PoC_ (central HCMC store) | ⬜ |
| WinMart | `storeCode`, `storeGroupCode` | _TBD at PoC_ (central HCMC store) | ⬜ |

---

## Allowed domains (cloud environment)

Mirror of `config/allowed-domains.txt`:
`bachhoaxanh.com`, `www.bachhoaxanh.com`, `apibhx.tgdd.vn`, `winmart.vn`,
`www.winmart.vn`, `api-crownx.winmart.vn`. Product images may load from CDN hosts
(e.g. `cdn.tgdd.vn`); if the crawler must fetch/verify an image, add that host here
**and** in `config/allowed-domains.txt`. (The dashboard just links image URLs — no
fetch needed for display.)

---

## Writing style for site copy (the agent's weekly note & UI text)

Vietnamese, **short and plain**. Say what changed and why it matters to a shopper.
No jargon, no hype. 2–4 sentences for the weekly note. Numbers rounded (e.g.
"tăng 1,2%"). See `docs/UI-DESIGN.md` for the full copy + visual style.
