# PoC Findings — Feasibility of crawling BHX & WinMart

> Verified 2026-07-03 via GitHub code search over real scrapers + live probes from
> the build sandbox. This is the **go/no-go evidence** for section 3 of the brief
> ("Rủi ro lớn nhất: chống bot"). Read this before writing any crawler code.

## TL;DR

- **Both sites expose an internal JSON API.** We do **not** need to parse HTML.
  This is the single most important finding — it de-risks the whole project.
- **Bách Hóa Xanh** → `https://apibhx.tgdd.vn` (Thế Giới Di Động / MWG backend).
  Needs a short-lived **bearer token** that is minted by the site's own JS, so the
  routine must open the site once in a headless browser to intercept the token,
  then call the API directly.
- **WinMart** → `https://api-crownx.winmart.vn` (Masan / CrownX backend). Plain
  `GET` with query params, no bearer token seen in public scrapers — lighter.
- **Both APIs are store-scoped**: prices depend on a `storeId` / `storeCode`. We
  must pin one store per chain (a large HCMC store) so the index compares
  like-for-like week over week.
- **Anti-bot**: real, but the API path is the soft underbelly. Plan for polite
  rate limits, a headless-browser token step for BHX, and a documented **local
  fallback** if the Anthropic datacenter IP gets blocked.

## 1. Bách Hóa Xanh — internal API

Confirmed from multiple independent public scrapers (`TranKietHCMUS/SHOOP`,
`PTIT-KLTN/SCRAPE-DATA`, `dnhuan/bachhoaxanh`, others). Host: **`apibhx.tgdd.vn`**.

### Required headers
```
Authorization: Bearer <TOKEN>        # short-lived, minted by site JS — see token step
deviceid:      <uuid>                # from cookie ck_bhx_us_log (.did) or a generated UUID
xapikey:       bhx-api-core-2022     # static app key seen across scrapers
origin:        https://www.bachhoaxanh.com
referer:       https://www.bachhoaxanh.com/
host:          apibhx.tgdd.vn
user-agent:    <realistic desktop Chrome UA>
```

### Endpoints (all under `https://apibhx.tgdd.vn`)
| Purpose | Method | Path + key params |
|---|---|---|
| Province list | GET | `/Location/V2/GetFull` |
| Stores in a province | GET | `/Location/V2/GetStoresByLocation?provinceId={id}` |
| Category tree for a store | GET | `/Menu/GetMenuV2?ProvinceId=&WardId=&StoreId=` |
| Products in a category | GET | `/Category/V2/GetCate?provinceId=3&wardId=0&districtId=0&storeId=2546&categoryUrl={slug}&isMobile=true&isV2=true&pageSize=300` |
| Products (paged) | POST | `/Category/AjaxProduct` body: `{provinceId, wardId, districtId, storeId, CategoryId, PageIndex, PageSize}` |

### Response shape
Products live at `data.products[]`. Confirmed product fields include `name`,
`unit`, `netUnitValue` (numeric net weight/volume used to derive unit price).
Price fields (`price`, `sysPrice`/original, `discountPercent`, stock flag) are
present on the object but **must be confirmed by dumping one live product JSON**
during PoC — do not hard-code names blind. See `CLAUDE.md` for the field-mapping
rule.

### Token acquisition (the crux)
The bearer token is **not static**. Public scrapers obtain it with a headless
browser (Playwright): open `https://www.bachhoaxanh.com`, let the page fire its
own API calls (`Menu/GetMenuV2`, `Location/V2/GetStoresByLocation`), and
intercept the `authorization` request header. `deviceid` is read from the
`ck_bhx_us_log` cookie (`.did`) or generated as a UUID fallback.

**Implication for the routine:** Playwright is pre-installed in the cloud
environment (`/opt/pw-browsers/chromium`). The `crawler-bhx` agent runs a small
token step first, caches the token for the run, then makes fast API calls. If the
browser step is blocked, that is the trigger to fall back to local execution.

## 2. WinMart — internal API

Confirmed from `phuc1131/smarthomechef` (`docs/CRAWL_WINMART.md`,
`crawl_winmart.py`). Host: **`api-crownx.winmart.vn`**.

### Endpoint
```
GET https://api-crownx.winmart.vn/it/api/web/v3/item/category
    ?orderByDesc=true
    &pageNumber=1
    &pageSize=100
    &slug={category-slug}          # e.g. rau-la--c01167
    &storeCode=1535
    &storeGroupCode=1998
```
Standard browser headers (UA, `origin`/`referer` = `https://winmart.vn`). No
bearer token observed in public scrapers — lighter than BHX. Confirm during PoC
whether a store-selection cookie is needed for prices.

### Response fields
`name`, `price`, `salePrice` (promo), `uom` / `uomName` (unit), `seoName` (slug
for the product detail URL). Pagination via `pageNumber` / `pageSize`.

## 3. Anti-bot & environment reality

- **From this build sandbox**, both `www.bachhoaxanh.com` and `winmart.vn` return
  `403` at the proxy CONNECT stage. Per `$HTTPS_PROXY/__agentproxy/status` this is
  a **sandbox egress-policy denial** (`gateway answered 403 to CONNECT`), *not* the
  sites' own bot wall. The real weekly routine runs in a **custom cloud
  environment where these domains are explicitly allow-listed**, so egress will be
  permitted there. This sandbox simply cannot be used to prove the sites' own
  tolerance — the live PoC must run inside the configured routine environment.
- The sites **do** have protection (server-side WebFetch also got 403; AdGuard
  ships a stealth/tracking rule for `apibhx.tgdd.vn`). Treat datacenter-IP
  blocking as a live risk, not a solved problem.
- `robots.txt` for both hosts was unreachable from here (same 403). Re-fetch and
  honor it during the in-environment PoC before scaling up.

### Mitigations baked into the plan
1. **Prefer the API over HTML** everywhere (fewer challenges, trivial parsing).
2. **Polite pacing**: 1 request / 2–3 s per host, realistic desktop UA, run in
   off-peak hours (early Saturday local time).
3. **BHX token via headless Chromium** (pre-installed) — mimics a real browser.
4. **Self-healing**: agents run a helper script first; on parse/HTTP failure they
   inspect the live response, fix the script, and commit (brief in section 8).
5. **Documented local fallback** (`docs/PLAN.md` §Fallback): same repo, same
   agents, run as a Desktop scheduled task on a residential IP if the cloud IP is
   blocked. Decision gate is the in-environment PoC.

## 4. Store pinning (decided)

Prices are store-specific on both chains. Pin one high-availability HCMC store per
chain for continuity; record the IDs in `CLAUDE.md` and never change them without
logging a methodology note (changing store = index break).

| Chain | Field(s) to pin | PoC action |
|---|---|---|
| BHX | `provinceId`, `storeId` (± ward/district) | Call `/Location/...` once, pick a central HCMC store, record IDs |
| WinMart | `storeCode`, `storeGroupCode` | Pick a central HCMC WinMart, record codes |

## 5. Sources

- AdGuard allowlist stealth rule for `apibhx.tgdd.vn` (confirms host + tracking posture)
- `TranKietHCMUS/SHOOP` — `extract_bhx.py` (headers, `/Category/V2/GetCate`, `/Category/AjaxProduct`, `data.products`)
- `PTIT-KLTN/SCRAPE-DATA` — `crawler/bhx/*` (`token_interceptor.py` Playwright token capture, `Location`/`Menu` endpoints, `process.py` field handling)
- `dnhuan/bachhoaxanh` — `getByProvince.py` (`/Location/V2/GetStoresByLocation`)
- `phuc1131/smarthomechef` — `docs/CRAWL_WINMART.md`, `crawl_winmart.py` (`api-crownx.winmart.vn/it/api/web/v3/item/category`, fields)
- Vietnam GSO / NSO — CPI 2020–2025 basket weights (food & catering 36.12%; lương thực 4.46%, thực phẩm 22.60%, ăn ngoài 9.06%); CEIC "Foods & Foodstuffs" weight 33.56% (2019=100)
