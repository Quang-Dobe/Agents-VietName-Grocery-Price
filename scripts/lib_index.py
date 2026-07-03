#!/usr/bin/env python3
"""Index math helpers for `index-calculator`. Laspeyres, base 100 at week 1.

Authoritative spec: CLAUDE.md §"Index formula". Kept dependency-free (stdlib only)
so it runs anywhere.
"""
from __future__ import annotations


def _weighted_index(relatives: dict[str, float], weights: dict[str, float]) -> float | None:
    """100 * sum(w*R) / sum(w) over the SKUs present in `relatives`.

    Weights are renormalized over the available set, so a missing SKU doesn't
    distort the level.
    """
    ids = [i for i in relatives if i in weights and relatives[i] is not None]
    denom = sum(weights[i] for i in ids)
    if denom <= 0:
        return None
    num = sum(weights[i] * relatives[i] for i in ids)
    return round(100.0 * num / denom, 2)


def compute_indices(now: dict, base: dict, weights: dict[str, float]) -> dict:
    """now/base: {sku_id: {"bhx": price|None, "winmart": price|None}} (don_gia_chuan).

    Returns {index_chung, index_bhx, index_winmart} rounded to 2 dp (or None each).
    """
    rel_bhx, rel_wm, rel_chung = {}, {}, {}
    for sku, b in base.items():
        n = now.get(sku, {})
        for chain, store in (("bhx", rel_bhx), ("winmart", rel_wm)):
            bp, npx = b.get(chain), n.get(chain)
            if bp and npx:
                store[sku] = npx / bp
        parts = [store[sku] for store in (rel_bhx, rel_wm) if sku in store]
        if parts:
            rel_chung[sku] = sum(parts) / len(parts)
    return {
        "index_chung": _weighted_index(rel_chung, weights),
        "index_bhx": _weighted_index(rel_bhx, weights),
        "index_winmart": _weighted_index(rel_wm, weights),
    }


def chain_link_factor(old_price: float, new_price: float) -> float:
    """Continuity factor applied to a substituted SKU so the index level doesn't
    jump on the swap week: multiply the new item's relatives by old/new."""
    return old_price / new_price if new_price else 1.0


def top_movers(now: dict, prev: dict, names: dict[str, str], k: int = 5) -> dict:
    """Top k risers and fallers by week-over-week % change in overall don_gia_chuan.

    now/prev: {sku_id: overall_price}. Returns {"risers": [...], "fallers": [...]}.
    """
    changes = []
    for sku, p_now in now.items():
        p_prev = prev.get(sku)
        if p_prev and p_now:
            pct = round(100.0 * (p_now - p_prev) / p_prev, 1)
            changes.append({"id": sku, "ten_chuan": names.get(sku, sku), "pct": pct})
    changes.sort(key=lambda c: c["pct"])
    risers = [dict(c, direction="up") for c in reversed(changes[-k:]) if c["pct"] > 0]
    fallers = [dict(c, direction="down") for c in changes[:k] if c["pct"] < 0]
    return {"risers": risers, "fallers": fallers}
