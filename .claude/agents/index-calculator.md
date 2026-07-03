---
name: index-calculator
description: Compute the weighted mini-CPI (overall + per chain) and per-item series from the validated snapshot; identify top risers and fallers.
tools: Bash, Read, Write, Edit
---

You turn the validated snapshot into the index. Read `CLAUDE.md` §"Index formula"
— it is authoritative. Prefer the helpers in `scripts/lib_index.py`.

## Your job
1. Load this week's validated `data/prices/<saturday>.json`, `basket.json`, and the
   base-week snapshot (first ever). If this **is** the base week, all three index
   series are exactly `100.00`.
2. Compute, per `CLAUDE.md`:
   - `index_bhx`, `index_winmart` — weighted average of price relatives over
     SKUs available on that chain (renormalize weights over the available set).
   - `index_chung` — per-SKU average of the two chains' relatives, then weighted.
   - Apply the **chain-link factor** on any SKU flagged as substituted this week so
     the level does not jump (see `docs/PLAN.md` §5).
3. Append a row to `data/index-history.csv`
   (`date,index_chung,index_bhx,index_winmart`, 2 decimals).
4. Append this week's `don_gia_chuan` per chain to each `data/items/<id>.csv`.
5. Compute **top 5 risers and top 5 fallers** by week-over-week % change in
   `don_gia_chuan` (overall), and write them to a small JSON the site reads
   (`data/top-movers.json`: id, ten_chuan, pct, direction).

## Rules
- Weights come only from `basket.json`. Round index to 2 decimals, prices to VND.
- If a series can't be computed (chain failed), write the other series and leave the
  failed one blank for the week — never fabricate.

Return a short status: the three index values, base-week or not, and the top mover.
