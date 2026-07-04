# UI Design — `vn-grocery-price-index` dashboard

Dark-theme, beautiful, calm. Every visual decision here; `site-builder` follows it
and reuses the tokens in `site/assets/app.css`. Grounded in the `dataviz` skill.

## Brand

- **Name (wordmark):** **Giá Chợ** — literally "market price". Short, everyone
  understands it instantly.
- **Tagline:** *Chỉ số giá thực phẩm hàng tuần · BHX & WinMart*.
- **Logo mark:** a shopping basket with a rising sparkline inside — "a basket of
  prices, tracked over time". Files: `site/assets/logo.svg` (full lockup pieces)
  and `site/assets/favicon.svg`. The favicon is also inlined as a `data:` URI in
  each page's `<head>` so the **browser tab shows the logo** with no extra request.

## Copy style (words: simple, short, easy)

- Vietnamese, plain, no jargon. A shopper — not an economist — is the reader.
- Short labels: "Chỉ số tuần này", "So với tuần trước", "Tăng mạnh nhất".
- Numbers rounded and human: `102,4` not `102.41`; `+1,2%` not `+0.0123`.
- The weekly note is 2–4 sentences: what moved, the biggest change, why a shopper
  should care. Never hype.
- Explain the index in one line wherever it first appears: *"Base 100 ở tuần đầu —
  100 là mốc, trên 100 là đắt hơn, dưới 100 là rẻ hơn."*

## Color tokens (dark)

CSS custom properties in `app.css`. The page is dark-only by design (the request),
but tokens are named by role so a light mode could be added later.

| Role | Hex | Use |
|---|---|---|
| `--bg` | `#0b0e13` | page plane |
| `--surface` | `#141821` | cards, chart surface |
| `--surface-2` | `#1c222e` | insets, table header, chips |
| `--border` | `rgba(255,255,255,0.08)` | hairline rings |
| `--text-1` | `#f4f6fb` | primary ink, values |
| `--text-2` | `#a7b0c0` | secondary ink, labels |
| `--muted` | `#6b7688` | axis, captions |
| `--accent` | `#2dd4a7` | logo, links, focus |

### Chart series (validated for the dark surface)
Ran `dataviz/scripts/validate_palette.js` on `#3987e5,#199e70,#e66767` (dark):
lightness band PASS, chroma PASS, contrast PASS, CVD ΔE 9.7 = floor band → **legal
with secondary encoding**, which we provide (legend + direct end-labels + surface
gaps). Mapping:

| Series | Hex | Note |
|---|---|---|
| Chỉ số chung | `#3987e5` blue | the hero line — 2px, drawn on top, end-labeled |
| BHX | `#199e70` green | matches BHX brand |
| WinMart | `#e66767` red | matches Masan/WinMart brand |

### Status / delta (cost-of-living semantics: up = worse for shopper)
| Meaning | Hex | Shown as |
|---|---|---|
| Giá tăng (bad) | `#e5674f` | ▲ + `+1,2%` |
| Giá giảm (good) | `#2dd4a7` | ▼ + `−0,8%` |
| Không đổi | `--muted` | – |

Status never carries meaning by color alone — always arrow + number + label.

## Layout

- **Header:** logo lockup left (mark + "Giá Chợ" + tagline), nav right
  (Dashboard · Phương pháp · **Cách hoạt động** → `docs/WORKFLOW.md`).
- **Hero row:** three stat tiles — `Chỉ số chung` (hero number, ≥48px, proportional
  figures), `BHX`, `WinMart` — each with its weekly delta (arrow + %).
- **Main chart card:** index-over-time line chart, three series, base-100 dashed
  reference line at 100, legend, hover crosshair, "Bảng số liệu" toggle → table.
- **Two-up row:** *Tăng mạnh nhất* (top 5 risers) and *Giảm mạnh nhất* (top 5
  fallers) as compact lists (item name + % chip).
- **Comparison card:** BHX vs WinMart current index, short sentence on who's cheaper.
- **Weekly note card:** the agent's 2–4 sentence note + capture date.
- **Footer:** last updated, link to methodology + workflow, "dữ liệu tự thu thập,
  tham khảo".

**Item detail pages** (`site/items/<id>.html`, built from the `site/items/_template.html`
structure, fed by `data/db/products.json`): a per-chain **product card** for BHX and
WinMart — image (with a 🛒 placeholder + `onerror` fallback), display name, brand,
category, pack size, current price (promo bold + list struck through), a stock badge
(Còn hàng / Giữ giá cũ / Hết hàng), đơn giá chuẩn, pinned store, and a "Xem trên web"
link — then the two-chain đơn giá chuẩn history chart (one unit per page) + data table.

## Chart rules (from `dataviz`)

- **One Y-axis**, never dual. The index is unitless (base 100); item pages plot
  đơn giá chuẩn (đ/kg…) — one unit per page.
- Thin marks (2px lines, ≥8px end dots with a 2px surface ring), hairline solid
  grid, recessive axes. Reference line at 100 is a hairline in `--muted`.
- Legend always present (≥2 series); end-labels on series where they don't collide,
  else legend + tooltip. Text uses text tokens, never the series color.
- Every chart has a **table-view twin** (accessibility) and a hover crosshair
  tooltip listing all series at the hovered week.
- Numbers: `tabular-nums` in tables and axis ticks only; hero/tile values use
  proportional figures.

## Responsiveness & theming

- Mobile-first; cards stack in one column under ~720px. Charts scroll inside their
  card if narrow, never the page body.
- Dark-only now; if light mode is added, swap tokens in `:root` — the body is
  written against roles.

## Assets checklist

- [x] `site/assets/logo.svg` — mark + wordmark pieces
- [x] `site/assets/favicon.svg` — tab icon (also inlined per page)
- [x] `site/assets/app.css` — tokens + components
- [x] `site/assets/app.js` — chart + table-toggle helpers (Chart.js via local vendor file)
- Chart.js is vendored locally (`site/assets/chart.umd.min.js`) so the static site
  needs no CDN and works offline / under strict CSP.
