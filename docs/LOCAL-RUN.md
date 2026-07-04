# Local run — add Bách Hóa Xanh from a home IP

BHX's price API (`apibhx.tgdd.vn`) **resets connections from datacenter IPs**, so
the weekly cloud routine is WinMart-only (see `research/POC-FINDINGS.md`). To also
collect **BHX**, run the crawl from a **residential IP** — your home machine — where
the API answers normally. Same repo, same code; only the runner changes.

## One-time setup

```bash
git clone https://github.com/Quang-Dobe/Agents-VietName-Grocery-Price
cd Agents-VietName-Grocery-Price
git checkout claude/website-design-docs-plan-v1ljj3

python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium        # for the BHX token step
```

You also need git push access to the repo (the run commits the weekly data).

## Weekly run

```bash
./scripts/run_local.sh
```

That does, in order:
1. **BHX** — `scripts/bhx_token.py` opens `bachhoaxanh.com` in headless Chromium and
   intercepts the API token, then `scripts/crawl_bhx.py` fetches the pinned store's
   category pages and matches your basket SKUs. (If BHX fails, the run continues
   WinMart-only — it never blocks the week.)
2. **WinMart** — `scripts/crawl_winmart.py` (works from anywhere).
3. **Render + publish** — `scripts/build_run.py` regenerates the static site and the
   run commits + pushes; GitHub Pages redeploys.

Run it weekly (Saturday morning). To automate on your machine: add a **cron** entry
(macOS/Linux) or a **Task Scheduler** task (Windows), e.g. cron:
```
0 8 * * 6  cd /path/to/Agents-VietName-Grocery-Price && ./scripts/run_local.sh >> run.log 2>&1
```

## First run: confirm two things (once)

Because BHX can't be tested from the cloud, two things are best-guessed and should
be confirmed on your first local run — both are logged to make it easy:

1. **The pinned store.** Defaults are `provinceId=3, storeId=2546` (a central HCMC
   store). To pick your own, list stores and pass them:
   ```bash
   python3 scripts/crawl_bhx.py --province 3 --store <your-store-id>
   ```
   The chosen store is recorded in `data/db/stores.json` — don't change it casually
   (changing store breaks the index; log it in `data/substitutions-log.md`).

2. **Category slugs + product fields.** Dump one live product to verify the field
   names in `scripts/crawl_bhx.py` (`to_chain_obj`) and the slugs in `BHX_CATS`:
   ```bash
   python3 scripts/crawl_bhx.py --dump
   ```
   The crawler also logs, per category, how many products came back — a `0` means
   that slug is wrong for this store; fix it in `BHX_CATS`. The matcher, unit-price
   parsing, and `match` hints in `basket.json` are shared with WinMart, so they work
   the same for BHX.

If you run this repo **with Claude Code locally**, the `crawler-bhx` agent will
self-heal these (inspect the live response, fix the slugs/fields, re-run) — that's
the intended first-run flow. Otherwise the two commands above take a few minutes by
hand.

## What you get

Once BHX is flowing, the dashboard's **BHX** tile and the **BHX vs WinMart**
comparison fill in, per-item pages show both chains side-by-side, and the overall
index averages the two chains per SKU (per `CLAUDE.md` §Index formula).
