# Run log

One entry per weekly run. Written by the routine (see `ROUTINE_PROMPT.md`).

Format:
```
## <YYYY-MM-DD>  (captured <ISO time>)
- BHX: <ok|failed> — <n>/<40> SKU
- WinMart: <ok|failed> — <n>/<40> SKU
- Substitutions: <n>  (see substitutions-log.md)
- Anomalies dropped: <n>
- Index: chung <v> · bhx <v> · winmart <v>
- Notes: <...>
```

<!-- runs appended below -->

## 2026-07-04  (captured 2026-07-04T06:00:00+07:00)
- WinMart: ok — 35/40 SKU
- BHX: blocked from cloud (apibhx.tgdd.vn resets datacenter IP); run locally — see docs/LOCAL-RUN.md
- Index: chung 100.00 · bhx — · winmart 100.00 (base week)
