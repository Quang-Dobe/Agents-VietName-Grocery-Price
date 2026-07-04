# vn-grocery-price-index — Giá Chợ

A weekly **mini-CPI** for a fixed basket of ~40 Vietnamese grocery SKUs, tracked
across **Bách Hóa Xanh** and **WinMart** online, published as a dark-theme static
dashboard on GitHub Pages. Built and run by **Claude Code Routines** +
multi-agent orchestration — no Claude API calls; the routine writes its own weekly
commentary.

> **Status: planning + scaffold.** This branch contains the detailed plan, the
> design specs, and runnable skeletons. Live crawling starts at the P0 PoC (see
> the plan). No prices have been collected yet.

## Start here

- **[`docs/PLAN.md`](docs/PLAN.md)** — the detailed plan: locked decisions, build
  order, acceptance criteria, risks.
- **[`docs/DATA-MODEL.md`](docs/DATA-MODEL.md)** — the two stores: current-state **DB**
  (`data/db/*.json`) vs **history** CSVs; what goes where and why.
- **[`docs/LOCAL-RUN.md`](docs/LOCAL-RUN.md)** — add **Bách Hóa Xanh** by running the
  crawl from a home/residential IP (`./scripts/run_local.sh`); BHX's API blocks the cloud.
- **[`docs/research/POC-FINDINGS.md`](docs/research/POC-FINDINGS.md)** — verified
  internal APIs (BHX `apibhx.tgdd.vn`, WinMart `api-crownx.winmart.vn`), anti-bot
  reality, and the cloud-vs-local decision gate.
- **[`docs/UI-DESIGN.md`](docs/UI-DESIGN.md)** — dark theme, logo, favicon, copy style.
- **[`docs/WORKFLOW.md`](docs/WORKFLOW.md)** — how the pipeline works (linked from the dashboard).

## Layout

```
.claude/agents/   5 subagents: crawler-bhx, crawler-winmart, validator,
                  index-calculator, site-builder
CLAUDE.md         schema, validation rules, store IDs, API field map, allowed domains
ROUTINE_PROMPT.md the weekly orchestration prompt
basket.json       the fixed basket — 40 SKUs, weights sum to 1.0
config/           allowed-domains.txt for the cloud environment
scripts/          crawl_winmart.py (live), crawl_bhx.py (+bhx_token.py, residential),
                  lib_match.py, lib_db.py, lib_index.py, build_run.py, run_local.sh
data/db/          products.json (details + current price), stores.json, meta.json  ← the "DB" (current)
data/             index-history.csv, items/<id>.csv  ← the history (time series)
site/             dark-theme dashboard (index.html), methodology.html, items/ (detail pages), assets/
docs/             PLAN.md, DATA-MODEL.md, UI-DESIGN.md, WORKFLOW.md, brief.md, research/
```

## Run the site locally

```
cd site && python3 -m http.server 8000   # then open http://localhost:8000
```
Chart.js is vendored (`site/assets/chart.umd.min.js`) — no CDN needed.

## How it runs (weekly)

`crawler-bhx` ‖ `crawler-winmart` → `validator` → `index-calculator` →
`site-builder` → commit to `main` → GitHub Pages redeploys. Details in
[`docs/WORKFLOW.md`](docs/WORKFLOW.md).
