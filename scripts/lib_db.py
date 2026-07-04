#!/usr/bin/env python3
"""File-based "DB" helpers: current-state JSON stores under data/db/.

The DB is current-state only — every writer OVERWRITES its store; we never keep
dated copies (see docs/DATA-MODEL.md). Time series live in the history CSVs, not
here. Stdlib only so it runs anywhere.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "db"
PRODUCTS = DB / "products.json"
STORES = DB / "stores.json"
META = DB / "meta.json"


def _read(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


# ----- products.json (details + current price, per SKU × chain) -----

def load_products() -> dict:
    return _read(PRODUCTS, {"updated": None, "items": []})


def upsert_chain(db: dict, sku_id: str, meta: dict, chain: str, payload: dict) -> dict:
    """Set one chain's side of one SKU without disturbing the other chain.

    `meta` carries the SKU's static fields (ten_chuan, nhom, don_vi_chuan); used only
    when the SKU is first seen this run. `payload` is the chain object (details +
    price). Returns the mutated db for chaining.
    """
    items = {it["id"]: it for it in db.get("items", [])}
    it = items.get(sku_id)
    if it is None:
        it = {**{k: meta.get(k) for k in ("ten_chuan", "nhom", "don_vi_chuan")}, "id": sku_id, "chains": {}}
        db.setdefault("items", []).append(it)
    it.setdefault("chains", {})[chain] = payload
    return db


def save_products(db: dict, updated: str) -> None:
    db["updated"] = updated
    _write(PRODUCTS, db)


def current_don_gia_chuan(db: dict) -> dict:
    """{sku_id: {"bhx": price|None, "winmart": price|None}} from the current DB."""
    out = {}
    for it in db.get("items", []):
        row = {}
        for chain in ("bhx", "winmart"):
            c = it.get("chains", {}).get(chain)
            row[chain] = (c or {}).get("don_gia_chuan")
        out[it["id"]] = row
    return out


# ----- stores.json -----

def load_stores() -> dict:
    return _read(STORES, {"updated": None, "stores": {}})


def set_store(chain: str, info: dict, updated: str) -> None:
    s = load_stores()
    s.setdefault("stores", {})[chain] = info
    s["updated"] = updated
    _write(STORES, s)


# ----- meta.json (idempotency) -----

def already_ran(week: str) -> bool:
    return _read(META, {}).get("last_run_week") == week


def mark_run(week: str, captured_at: str) -> None:
    _write(META, {"last_run_week": week, "captured_at": captured_at})


if __name__ == "__main__":
    # tiny self-check
    db = {"updated": None, "items": []}
    upsert_chain(db, "gao-st25-5kg", {"ten_chuan": "Gạo ST25", "nhom": "Gạo", "don_vi_chuan": "kg"},
                 "bhx", {"don_gia_chuan": 35000, "trang_thai": "in_stock"})
    upsert_chain(db, "gao-st25-5kg", {}, "winmart", {"don_gia_chuan": 37800, "trang_thai": "in_stock"})
    print(json.dumps(current_don_gia_chuan(db), ensure_ascii=False))
