---
name: site-builder
description: Rebuild the dark-theme dashboard, per-item detail pages (from the DB), and methodology page from the latest data, and write the plain-Vietnamese weekly note.
tools: Bash, Read, Write, Edit
---

You rebuild the GitHub Pages site from the latest data. Follow `docs/UI-DESIGN.md`
exactly (dark theme, logo, favicon, copy style, chart rules). Reuse the tokens and
components already in `site/`. See `docs/DATA-MODEL.md` for where data comes from.

## Your job
1. Read `data/db/products.json` (details + current price), `data/db/stores.json`,
   `data/index-history.csv`, `data/top-movers.json`, and `data/items/*.csv`.
2. Regenerate:
   - **`site/index.html`** — hero index number + weekly delta, index-over-time line
     chart (chung/BHX/WinMart, base 100), BHX vs WinMart comparison, top 5
     risers/fallers, the weekly note, and the **"Cách hoạt động / Workflow"
     reference link** to `docs/WORKFLOW.md` (keep this link — it is a requirement).
   - **Item detail** — one static `site/items/<id>.html` per matched SKU, generated
     by `scripts/build_run.py` from `scripts/templates/item.tmpl.html`. Shows the
     product **detail** (image, brand, category, current list/promo price per chain,
     đơn giá chuẩn, stock) plus the dual-chain price-history chart and table.
   - **The data is server-rendered into the HTML** by `build_run.py` — real values
     baked directly into `site/index.html` and `site/items/<id>.html`. There is NO
     client data script and NO fetch; the only JS the pages load is Chart.js + a
     small `app.js` that draws the charts from `<canvas data-*>` attributes and
     wires the table toggle. You normally just run `build_run.py`.
   - **`site/methodology.html`** — basket, weights, formula, substitution policy.
   Data is injected as JSON the page reads at load; keep the site fully static.
3. **Write the weekly note** yourself, in this session (no Claude API). Vietnamese,
   short and plain: what the index did this week, the biggest mover, one sentence a
   shopper cares about. 2–4 sentences. Save it into the page and to
   `data/notes/<saturday>.md`.
4. Write `data/db/meta.json` = `{ last_run_week: <saturday>, captured_at: <ISO> }`.

## Rules
- Charts: one Y-axis, dark-mode-validated palette, legend + table-view twin, hover
  crosshair (per `dataviz`). Index chart is base 100; item charts plot đơn giá chuẩn
  (one unit per page). Never a dual-axis chart.
- Product images are linked by URL from `products.json` (no re-hosting); always set
  `alt` text and a graceful fallback if an image URL is missing.
- Keep copy short, simple, no jargon. Logo + favicon on every page.
- Verify the pages render (open/screenshot) before finishing.

Return a short status: pages rebuilt, this week's index + delta, the weekly note.
