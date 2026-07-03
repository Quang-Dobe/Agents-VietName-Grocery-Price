# Substitutions log

Every time a SKU is swapped for an equivalent, it is recorded here so the index
stays auditable. Substitution rules: same group + comparable pack size, chain-link
at the swap (see `docs/PLAN.md` §5).

Format:
```
## <YYYY-MM-DD> — <sku-id> (<chain>)
- Cũ: <old name / url>
- Mới: <new name / url>
- Lý do: <out of stock | delisted | url changed | ...>
- Nối chuỗi: hệ số <old_price>/<new_price> = <factor>
```

<!-- substitutions appended below -->
