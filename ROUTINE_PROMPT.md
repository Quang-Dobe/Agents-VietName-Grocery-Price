# ROUTINE_PROMPT — weekly grocery price index

Paste this as the Routine prompt. Trigger: **weekly, Saturday ~05:00
Asia/Ho_Chi_Minh**, plus a **Sunday safety re-run** with the same prompt (the
idempotency check makes the Sunday run a no-op if Saturday already succeeded).

---

You are running the weekly `vn-grocery-price-index` pipeline. Read `CLAUDE.md`
before doing anything — it holds the schema, the two data stores (DB vs history),
store IDs, API map, and rules. See `docs/DATA-MODEL.md` for the DB/history split.
All work goes onto a fresh weekly branch and is published as a **normal (non-draft)
pull request** — the auto-merge workflow merges it into `main` once checks pass, and
GitHub Pages redeploys automatically.

## Step 0 — idempotency guard
Compute this week's Saturday date (Asia/Ho_Chi_Minh). If `data/db/meta.json`
`last_run_week` equals it, print "already ran this week, exiting" and **stop**.
(This makes the Sunday safety run a no-op after a good Saturday run.)

## Step 1 — crawl (parallel)
Launch **`crawler-bhx`** and **`crawler-winmart`** in parallel (one message, two
tool calls). Each fetches, for every basket SKU on its chain, the **product detail**
(name, brand, category, image, unit, url) **and the current price**, and writes its
chain's side of `data/db/products.json` (current state, overwritten). Each also
records its pinned store in `data/db/stores.json`. Enforce polite pacing; if a chain
is blocked (repeated 403/429), let that crawler log the failure and exit — the
pipeline continues with the chain that worked.

## Step 2 — validate
Run **`validator`**. It compares `data/db/products.json` against the last row of
each `data/items/<id>.csv` (previous week), flags/repairs anomalies (>50% jumps,
sanity band), applies carry-forward, writes corrections back into `products.json`,
and logs every decision. Wait for it to finish.

## Step 3 — compute the index
Run **`index-calculator`**. It reads current `don_gia_chuan` from `products.json`
and base-week values from the first row of each `data/items/<id>.csv`, appends to
`data/index-history.csv`, appends this week's row to each `data/items/<id>.csv`,
writes `data/top-movers.json`, and applies chain-link factors for any substitutions.
Week 1 → all three series = 100.00.

## Step 4 — build the site
Run **`site-builder`** (which runs `python scripts/build_run.py`). It **renders the
dashboard and per-item pages as static HTML with the real values baked in** — from
`data/db/products.json` + the history CSVs — writes the plain-Vietnamese weekly
note, and keeps the **Workflow link** (`workflow.html`) on the dashboard. No client
data script and no fetch; charts read `<canvas data-*>` attributes. It verifies the
page renders.

## Step 5 — commit, open a PR & log
- Append a run summary to `data/run-log.md` (date, sources ok/fail, SKUs captured,
  substitutions, index values).
- Write `data/db/meta.json` = `{ last_run_week: <saturday>, captured_at: <ISO> }`.
- Create a fresh branch for this run (e.g. `data/weekly-update-<saturday>`) off the
  latest `main`. Commit everything with a message like
  `data: weekly update <saturday> (index_chung <value>)` and push the branch.
- Open a **normal (non-draft) pull request** into `main` with that same title and a
  short body summarizing sources ok/fail, SKUs captured, and the index values. Do
  **not** open it as a draft — the auto-merge workflow only merges non-draft PRs.
- The `auto-merge` workflow (`.github/workflows/auto-merge.yml`) merges the PR into
  `main` once checks pass; GitHub Pages then redeploys automatically.
- If Pages doesn't update, note it in the run log; do not retry destructively.

## Guardrails
- Never invent prices — a missing SKU is `out_of_stock`, logged.
- **DB is current-only:** overwrite `data/db/*.json`; never write a dated copy.
- Never change a pinned store ID without logging a methodology note.
- If **both** chains are blocked, write a run-log entry explaining it and stop
  without touching `meta.json` — this is the signal to evaluate the local fallback
  (see `docs/PLAN.md` §7).
