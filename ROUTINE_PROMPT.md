# ROUTINE_PROMPT — weekly grocery price index

Paste this as the Routine prompt. Trigger: **weekly, Saturday ~05:00
Asia/Ho_Chi_Minh**, plus a **Sunday safety re-run** with the same prompt (the
idempotency check makes the Sunday run a no-op if Saturday already succeeded).

---

You are running the weekly `vn-grocery-price-index` pipeline. Read `CLAUDE.md`
before doing anything — it holds the schema, store IDs, API map, and rules. All
work commits straight to `main`; GitHub Pages redeploys automatically.

## Step 0 — idempotency guard
Compute this week's Saturday date (Asia/Ho_Chi_Minh). If
`data/prices/<saturday>.json` already exists **and** contains prices for both
chains, print "snapshot already exists, exiting" and **stop**. (This makes the
Sunday safety run a no-op after a good Saturday run.)

## Step 1 — crawl (parallel)
Create the empty snapshot `data/prices/<saturday>.json` scaffold, then launch
**`crawler-bhx`** and **`crawler-winmart`** in parallel (one message, two tool
calls). Each fills its own chain's side of every SKU. Enforce polite pacing; if a
chain is blocked (repeated 403/429), let that crawler log the failure and exit —
the pipeline continues with the chain that worked.

## Step 2 — validate
Run **`validator`** on the snapshot. It flags/repairs anomalies (>50% jumps, sanity
band), applies carry-forward, and logs every decision. Wait for it to finish.

## Step 3 — compute the index
Run **`index-calculator`**. It appends to `data/index-history.csv`, updates
per-item CSVs, writes `data/top-movers.json`, and applies chain-link factors for
any substitutions. Week 1 → all three series = 100.00.

## Step 4 — build the site
Run **`site-builder`**. It rebuilds the dark-theme dashboard, per-item pages, and
methodology page, writes the plain-Vietnamese weekly note, and keeps the
**Workflow reference link** on the dashboard. It verifies the page renders.

## Step 5 — commit & log
- Append a run summary to `data/run-log.md` (date, sources ok/fail, SKUs captured,
  substitutions, index values).
- Commit everything to `main` with a message like
  `data: weekly snapshot <saturday> (index_chung <value>)` and push.
- If Pages doesn't update, note it in the run log; do not retry destructively.

## Guardrails
- Never invent prices — a missing SKU is `out_of_stock`, logged.
- Never change a pinned store ID without logging a methodology note.
- If **both** chains are blocked, write a run-log entry explaining it and stop
  without committing an empty snapshot — this is the signal to evaluate the local
  fallback (see `docs/PLAN.md` §7).
