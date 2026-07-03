# Detail Plan — `vn-grocery-price-index`

Weekly mini-CPI for a fixed grocery basket, tracked across **Bách Hóa Xanh** and
**WinMart** online, published as a dark-theme static dashboard on GitHub Pages.
Built and run entirely by Claude Code Routines + multi-agent orchestration — **no
Claude API calls**.

This document is the plan the brief asked for. It turns the brief
(`docs/brief.md`) into locked decisions, a concrete build order, and acceptance
criteria. Feasibility research that backs the key choices lives in
[`research/POC-FINDINGS.md`](research/POC-FINDINGS.md).

---

## 0. Decisions locked (was §9 of the brief)

| # | Question | Decision |
|---|---|---|
| 1 | SKU list + weights | **40 SKUs, 14 groups**, weights grounded in GSO CPI food structure — see §3 and `basket.json`. |
| 2 | SKU substitution policy | Substitute only within the same group + comparable pack size; **chain-link** the index at the swap so the level never jumps — see §5. |
| 3 | Add Co.op / other chains? | **No, not now.** Ship BHX + WinMart stable first. Schema leaves room to add a chain later. |
| 4 | robots.txt / ToS / pace | Re-check robots in-environment at PoC; crawl **1 req / 2–3 s per host**, off-peak, identifying UA. See `POC-FINDINGS.md` §3. |
| 5 | Cloud vs local | **Cloud-first** (APIs found, Playwright pre-installed). Ship the **local Desktop fallback** documented and ready; the in-environment PoC is the decision gate. See §7. |

Both target chains expose an internal JSON API (BHX `apibhx.tgdd.vn`, WinMart
`api-crownx.winmart.vn`), so the crawler parses JSON, not HTML — the biggest risk
in the brief is substantially reduced. Details and evidence:
[`research/POC-FINDINGS.md`](research/POC-FINDINGS.md).

---

## 1. Goal & scope

- Track a **fixed basket of ~40 SKUs** at BHX and WinMart **every week**.
- Compute a **self-made cost-of-living index** (mini-CPI, base 100 at week 1),
  overall and per chain.
- Publish a **dark-theme dashboard** + per-item history + methodology page to
  GitHub Pages.
- The routine **writes its own weekly commentary** in-session (no Claude API).
- **No backfill.** History accumulates from the first run onward.

Out of scope for v1: extra chains, mobile app, alerts, user accounts.

---

## 2. Architecture at a glance

```
Claude Code Routine (weekly, Sat + Sun safety re-run)
        │
        ├─ crawler-bhx      ─┐  run in parallel
        ├─ crawler-winmart  ─┘  → data/prices/<date>.json (raw per-SKU × chain)
        │
        ├─ validator            → flags/repairs anomalies, writes decisions
        ├─ index-calculator     → data/index-history.csv (+ per-item series)
        └─ site-builder         → site/*.html (dashboard, items, methodology)
        │
        └─ commit to main → GitHub Pages redeploys
```

Five subagents, defined in `.claude/agents/*.md`, orchestrated by
`ROUTINE_PROMPT.md`. Shared rules, schema, store IDs, and validation thresholds
live in `CLAUDE.md` so every agent reads from one source of truth.

---

## 3. The basket (most important design work)

`basket.json` holds **40 SKUs across 14 groups**. Group weights are anchored to
the Vietnam GSO CPI 2020–2025 structure (food & catering 36.12% → lương thực
4.46%, thực phẩm 22.60%, dining-out 9.06% which we exclude as we only track
in-home groceries), then renormalized to sum to 1.0 and extended with household
essentials (a real weekly-spend category not in "food").

| Group (VI) | Weight | SKUs | Rationale |
|---|---:|---:|---|
| Gạo & lương thực | 0.12 | 3 | Staple; GSO lương thực block |
| Thịt heo | 0.15 | 4 | Largest single protein in VN diet |
| Thịt gà | 0.08 | 3 | Second protein |
| Thịt bò | 0.06 | 2 | Premium protein, smaller share |
| Cá & thủy sản | 0.09 | 3 | Major protein in VN |
| Trứng | 0.05 | 2 | Cheap daily protein |
| Rau củ | 0.11 | 5 | High-frequency, price-volatile |
| Trái cây | 0.06 | 3 | Regular fresh spend |
| Dầu ăn | 0.04 | 2 | Core cooking input |
| Gia vị (nước mắm, đường, muối, bột ngọt) | 0.06 | 4 | Pantry staples |
| Sữa | 0.06 | 3 | Dairy / child nutrition |
| Mì gói | 0.03 | 2 | Convenience staple |
| Cà phê | 0.02 | 1 | Everyday beverage |
| Đồ dùng thiết yếu (giấy VS, nước rửa chén) | 0.07 | 3 | Non-food weekly essentials |
| **Total** | **1.00** | **40** | |

Per-SKU weight = group weight split across its SKUs (see `basket.json`; SKU
weights within a group sum to the group weight, all 40 sum to 1.0).

**Schema handles the hard cases** (full schema + rules in `CLAUDE.md`):
- **Promo vs list price** — store both `gia_niem_yet` and `gia_khuyen_mai`; the
  index uses the price a shopper actually pays (promo if present, else list).
- **Unit normalization** — convert every price to a standard unit
  (đ/kg, đ/lít, đ/quả) via `don_vi_chuan` + pack size, so BHX and WinMart are
  comparable even when pack sizes differ.
- **Out of stock** — mark `out_of_stock`; carry the last known price forward for
  **max 2 weeks**, then drop the SKU from that period's index and log it.

---

## 4. Data & files

```
basket.json                     # basket definition (every change is version-controlled)
data/prices/<YYYY-MM-DD>.json   # weekly snapshot: all SKUs × 2 chains, raw + normalized
data/index-history.csv          # date, index_chung, index_bhx, index_winmart
data/items/<sku-id>.csv         # per-SKU price history (both chains) for detail charts
data/substitutions-log.md       # every SKU swap, with reason + old/new URL
data/run-log.md                 # per-run: sources ok/fail, SKUs captured, notes
```

**Index formula** — simple Laspeyres, base 100 at week 1. For each SKU the price
relative is `price_now / price_base`; the index is the weighted average of
relatives using basket weights. Computed three ways: BHX-only, WinMart-only, and
overall (per-SKU average of the two chains, then weighted). Full worked formula in
the methodology page and `CLAUDE.md`.

---

## 5. Substitution & continuity (decision #2, expanded)

When a SKU disappears or changes URL, `crawler-*` may substitute **within the same
group and a comparable pack size** (e.g. one 5 kg rice for another 5 kg rice of
similar tier). Rules:

1. Record old → new in `data/substitutions-log.md` with reason and date.
2. Update the SKU's `urls` in `basket.json`; keep the same `id` so the series
   stays continuous.
3. **Chain-link at the swap**: rebase the new item's relative so the index level
   does not jump on substitution week (continuity factor = old price / new price
   at the overlap). This is the standard CPI technique and keeps the index honest.
4. If no comparable substitute exists, mark `out_of_stock` and follow the
   carry-forward rule (§3).

---

## 6. Static site (GitHub Pages)

Full visual spec (dark theme, logo, favicon, copy style, chart rules) is in
[`UI-DESIGN.md`](UI-DESIGN.md). The `site/` template is built to that spec.

- **`index.html` (dashboard):** hero index number + weekly delta, index-over-time
  line chart, BHX vs WinMart comparison, top 5 risers / fallers, the agent's
  weekly note, **and a "Cách hoạt động / Workflow" reference link** to the
  workflow docs (per the request).
- **`items/<sku>.html`:** dual-chain price history (Chart.js), data table.
- **`methodology.html`:** basket, weights, formula, substitution policy — this is
  what makes the index credible.

Charts follow the `dataviz` skill: one Y-axis, indexed to base 100, categorical
palette validated for dark mode, legend + table-view twin, hover crosshair.

---

## 7. Execution: cloud-first, local fallback

**Cloud (default):**
- One weekly Routine, **Saturday** early morning (Asia/Ho_Chi_Minh), + a **Sunday
  safety re-run** that exits early if `data/prices/<this-week>.json` already
  exists.
- Custom cloud environment with **allow-listed domains** (`config/allowed-domains.txt`).
- **Unrestricted branch push** → commit straight to `main` → Pages redeploys.
- BHX token step uses the **pre-installed Playwright Chromium**.

**Local fallback (ready, not default):** if the in-environment PoC shows the
datacenter IP is blocked, run the *same repo, same agents* as a **Desktop
scheduled task** on a residential IP. Only the trigger/runner changes; all agent
logic, schema, and site code are reused. Requires the machine to be on at run
time. Decision gate: PoC result in §PoC below.

---

## 8. Self-healing crawlers

Each `crawler-*` agent: (1) runs `scripts/crawl_<chain>.py` for the fast path;
(2) on HTTP/parse failure, fetches one live response, diffs it against the
expected shape, **rewrites the script**, re-runs, and **commits the fix** with a
clear message. This is the agent advantage over a static script — the pipeline
repairs itself when the site changes instead of silently failing. Guardrails and
the field-mapping contract are in `CLAUDE.md`.

---

## 9. Build order & acceptance

| Phase | Deliverable | Done when |
|---|---|---|
| **P0 PoC** | In-environment probe of both APIs from the routine env: token step for BHX, store pinning, one live product JSON per chain, robots re-check | We have real prices for ≥5 SKUs per chain and confirmed price field names; cloud-vs-local decided |
| **P1 Schema** | `basket.json` finalized with real URLs + store IDs; `CLAUDE.md` field map confirmed | 40 SKUs resolve to live products on both chains (or logged substitution) |
| **P2 Crawl** | `crawler-bhx`, `crawler-winmart` + `scripts/` produce `data/prices/<date>.json` | Snapshot has both chains, promo+list, normalized unit price |
| **P3 Index** | `validator` + `index-calculator` → `index-history.csv`, per-item CSVs | Week-1 index = 100.0 on all three series; anomalies logged |
| **P4 Site** | `site-builder` → dashboard + items + methodology, dark theme, logo, favicon, workflow link | Pages renders; charts populated; weekly note present |
| **P5 Automate** | Routine schedule (Sat + Sun safety) + allow-list live | Two consecutive weekly runs commit clean snapshots unattended |

**Acceptance for v1:** three unattended weekly runs produce valid snapshots, the
index updates, and the dashboard redeploys with a fresh agent-written note — with
no manual intervention.

---

## 10. Risks & mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Datacenter IP blocked | Medium | API-first + Playwright token + polite pace; local fallback ready (§7) |
| BHX token expires mid-run | Medium | Re-intercept per run; retry once on 401 |
| Price field names differ from assumption | Low | PoC dumps live JSON; `CLAUDE.md` field map is the single place to fix |
| SKU vanishes | Medium | Substitution + chain-link (§5); carry-forward ≤ 2 wk |
| Site markup/API changes | Low-Med | Self-healing crawlers (§8) commit repairs |
| Store-scoped price drift | Low | Pinned store IDs in `CLAUDE.md`; changing a store logs a methodology note |

---

## 11. Repo map

```
.claude/agents/     crawler-bhx.md, crawler-winmart.md, validator.md,
                    index-calculator.md, site-builder.md
CLAUDE.md           schema, validation rules, store IDs, API field map, allowed domains
ROUTINE_PROMPT.md   the weekly orchestration prompt
basket.json         basket definition (40 SKUs)
config/allowed-domains.txt
scripts/            crawl_bhx.py, crawl_winmart.py, bhx_token.py, lib_index.py (skeletons)
data/               prices/, items/, index-history.csv, logs
site/               index.html, methodology.html, items/, assets/ (logo, favicon, css, js)
docs/               PLAN.md (this file), UI-DESIGN.md, WORKFLOW.md, research/POC-FINDINGS.md
```
