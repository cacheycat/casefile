"""The case graph: addresses as nodes, aggregated value flows as edges.

Built deterministically from fetched transfers. Structural features that feed
the triage prompt (and the heuristic fallback) are computed here, not by the
model, so every number in a report has a code path behind it.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime


def _ts(iso: str | None) -> float:
    if not iso:
        return 0.0
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


class CaseGraph:
    def __init__(self, eth_usd: float):
        self.eth_usd = eth_usd
        self.nodes: dict[str, dict] = {}
        self.edges: dict[tuple[str, str], dict] = {}
        self.transfers: dict[str, list[dict]] = defaultdict(list)  # per expanded address

    def ensure(self, h: str, party: dict | None = None, depth: int | None = None) -> dict:
        n = self.nodes.setdefault(h, {"hash": h, "expanded": False, "depth": depth,
                                      "name": None, "ens": None, "contract": False, "verified": False,
                                      "scam_flag": False, "tags": [], "in_usd": 0.0, "out_usd": 0.0,
                                      "tx_seen": 0, "first_ts": None, "last_ts": None})
        if party:
            for k in ("name", "ens", "tags"):
                n[k] = party.get(k) or n[k]
            n["contract"] = n["contract"] or bool(party.get("contract"))
            n["verified"] = n["verified"] or bool(party.get("verified"))
            n["scam_flag"] = n["scam_flag"] or bool(party.get("scam_flag"))
        if depth is not None and (n["depth"] is None or depth < n["depth"]):
            n["depth"] = depth
        return n

    def usd(self, row: dict) -> float:
        if row.get("usd") is not None:
            return float(row["usd"])
        if row["unit"] == "ETH":
            return row["amount"] * self.eth_usd
        return 0.0

    def add_transfers(self, center: str, rows: list[dict], depth: int) -> int:
        added = 0
        for r in rows:
            src, dst = (r["from"] or {}).get("hash"), (r["to"] or {}).get("hash")
            if not src or not dst or src == dst:
                continue
            usd = self.usd(r)
            if r["amount"] <= 0:
                continue
            self.ensure(src, r["from"], depth + (src != center))
            self.ensure(dst, r["to"], depth + (dst != center))
            e = self.edges.setdefault((src, dst), {"from": src, "to": dst, "usd": 0.0, "count": 0,
                                                   "units": set(), "first_ts": None, "last_ts": None})
            e["usd"] += usd
            e["count"] += 1
            e["units"].add(r["unit"])
            ts = _ts(r.get("ts"))
            if ts:
                e["first_ts"] = min(e["first_ts"] or ts, ts)
                e["last_ts"] = max(e["last_ts"] or ts, ts)
            for h in (src, dst):
                n = self.nodes[h]
                n["tx_seen"] += 1
                if ts:
                    n["first_ts"] = min(n["first_ts"] or ts, ts)
                    n["last_ts"] = max(n["last_ts"] or ts, ts)
            self.nodes[dst]["in_usd"] += usd
            self.nodes[src]["out_usd"] += usd
            self.transfers[center].append(r)
            added += 1
        return added

    def features(self, h: str) -> dict:
        """Structural facts about a frontier node, for triage and the report."""
        n = self.nodes[h]
        ins = [e for e in self.edges.values() if e["to"] == h]
        outs = [e for e in self.edges.values() if e["from"] == h]
        in_usd, out_usd = sum(e["usd"] for e in ins), sum(e["usd"] for e in outs)
        through = min(in_usd, out_usd)
        span_h = None
        if n["first_ts"] and n["last_ts"]:
            span_h = round((n["last_ts"] - n["first_ts"]) / 3600, 1)
        return {"address": h, "name": n["name"], "contract": n["contract"], "verified": n["verified"],
                "scam_flag": n["scam_flag"], "tags": n["tags"], "depth": n["depth"],
                "counterparties_in": len(ins), "counterparties_out": len(outs),
                "in_usd": round(in_usd), "out_usd": round(out_usd),
                "passthrough_ratio": round(through / max(in_usd, out_usd), 2) if max(in_usd, out_usd) > 0 else 0.0,
                "fan_in": len(ins), "fan_out": len(outs), "activity_span_hours": span_h,
                "tx_seen": n["tx_seen"]}

    def frontier(self) -> list[dict]:
        rows = [self.features(h) for h, n in self.nodes.items() if not n["expanded"] and not n["contract"]]
        return sorted(rows, key=lambda f: -(f["in_usd"] + f["out_usd"]))

    def to_json(self) -> dict:
        edges = []
        for e in self.edges.values():
            edges.append({**e, "units": sorted(e["units"]), "usd": round(e["usd"], 2)})
        return {"nodes": list(self.nodes.values()), "edges": edges, "eth_usd": self.eth_usd}
