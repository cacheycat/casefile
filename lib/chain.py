"""Ethereum data via Blockscout's public REST API, with an on-disk snapshot.

Every response is cached under data/snapshots. A demo case replays entirely
from the snapshot, so the UI works offline and the eval suite is reproducible;
a fresh address fetches live and becomes part of the snapshot.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from agentkit.http import fetch_json

BASE = "https://eth.blockscout.com/api/v2"
SNAP = Path(__file__).resolve().parent.parent / "data" / "snapshots"
DEMO = Path(__file__).resolve().parent.parent / "demo" / "snapshots"  # committed, read-only
PAGE_LIMIT = 2  # pages per endpoint per address: enough signal, bounded cost

_ADDR = re.compile(r"^0x[0-9a-fA-F]{40}$")


def valid_address(a: str) -> bool:
    return bool(_ADDR.match(a or ""))


def _cached(url: str) -> dict:
    SNAP.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha1(url.encode()).hexdigest()[:24]
    path = SNAP / f"{key}.json"
    if path.exists():
        return json.loads(path.read_text())
    if (DEMO / path.name).exists():
        return json.loads((DEMO / path.name).read_text())
    out = fetch_json(url)
    path.write_text(json.dumps(out))
    return out


def _pages(path: str, params: str = "") -> list[dict]:
    items, next_params = [], None
    for _ in range(PAGE_LIMIT):
        url = f"{BASE}{path}?{params}" if params else f"{BASE}{path}"
        if next_params:
            qp = "&".join(f"{k}={v}" for k, v in next_params.items())
            url = f"{BASE}{path}?{params + '&' if params else ''}{qp}"
        out = _cached(url)
        items += out.get("items", [])
        next_params = out.get("next_page_params")
        if not next_params:
            break
    return items


def _party(p: dict | None) -> dict:
    """Reduce Blockscout's address object to what the case needs. Names and
    tags are display data from the explorer: shown, never trusted as facts."""
    if not p:
        return {"hash": None}
    tags = [t.get("name") for t in (p.get("metadata") or {}).get("tags", []) if t.get("name")]
    name = p.get("name") or (tags[0] if tags else None) or p.get("ens_domain_name")
    return {"hash": (p.get("hash") or "").lower(), "name": name, "ens": p.get("ens_domain_name"),
            "contract": bool(p.get("is_contract")), "verified": bool(p.get("is_verified")),
            "scam_flag": bool(p.get("is_scam")) or p.get("reputation") not in (None, "ok"),
            "tags": tags[:4]}


def profile(address: str) -> dict:
    a = _cached(f"{BASE}/addresses/{address}")
    counters = {}
    try:
        counters = _cached(f"{BASE}/addresses/{address}/counters")
    except RuntimeError:
        pass
    return {**_party(a), "balance_eth": round(int(a.get("coin_balance") or 0) / 1e18, 4),
            "tx_count": int(str(counters.get("transactions_count") or 0) or 0)}


def transactions(address: str) -> list[dict]:
    rows = []
    for t in _pages(f"/addresses/{address}/transactions"):
        if t.get("status") == "error":
            continue
        rows.append({"hash": t["hash"], "ts": t.get("timestamp"), "kind": "eth",
                     "from": _party(t.get("from")), "to": _party(t.get("to")),
                     "amount": round(int(t.get("value") or 0) / 1e18, 6), "unit": "ETH",
                     "method": t.get("method")})
    return rows


def token_transfers(address: str) -> list[dict]:
    rows = []
    for t in _pages(f"/addresses/{address}/token-transfers", "type=ERC-20"):
        token = t.get("token") or {}
        total = t.get("total") or {}
        try:
            dec = int(total.get("decimals") or token.get("decimals") or 18)
            amount = int(total.get("value") or 0) / 10 ** dec
        except (TypeError, ValueError):
            continue
        rate = token.get("exchange_rate")
        rows.append({"hash": t.get("transaction_hash"), "ts": t.get("timestamp"), "kind": "erc20",
                     "from": _party(t.get("from")), "to": _party(t.get("to")),
                     "amount": round(amount, 6), "unit": str(token.get("symbol") or "?")[:12],
                     "usd": round(amount * float(rate), 2) if rate else None,
                     "token_name": str(token.get("name") or "")[:60],
                     "token_reputation": token.get("reputation"), "method": t.get("method")})
    return rows


def eth_price() -> float:
    try:
        a = _cached(f"{BASE}/addresses/0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045")
        return float(a.get("exchange_rate") or 0)
    except (RuntimeError, TypeError, ValueError):
        return 0.0
