import pytest

from lib.graphmodel import CaseGraph

A, B, C = "0xa", "0xb", "0xc"


def tx(src, dst, amount, unit="ETH", ts=None, usd=None):
    return {"from": {"hash": src} if src else None, "to": {"hash": dst} if dst else None,
            "amount": amount, "unit": unit, "ts": ts, "usd": usd}


@pytest.fixture()
def graph():
    g = CaseGraph(eth_usd=2000.0)
    g.add_transfers(A, [
        tx(A, B, 1.0, ts="2024-01-01T00:00:00Z"),
        tx(B, C, 0.9, ts="2024-01-01T01:00:00Z"),
    ], depth=0)
    return g


def test_edges_aggregate_value_and_count(graph):
    graph.add_transfers(A, [tx(A, B, 0.5)], depth=0)
    e = graph.edges[(A, B)]
    assert e["count"] == 2 and e["usd"] == pytest.approx(3000.0)


def test_degenerate_rows_are_ignored():
    g = CaseGraph(2000.0)
    added = g.add_transfers(A, [tx(A, A, 5), tx(A, B, 0), tx(None, B, 1), tx(A, None, 1)], depth=0)
    assert added == 0 and not g.edges


def test_passthrough_ratio_flags_relay_wallets(graph):
    f = graph.features(B)
    assert f["passthrough_ratio"] == pytest.approx(0.9)
    assert f["fan_in"] == 1 and f["fan_out"] == 1 and f["activity_span_hours"] == 1.0


def test_token_rows_use_supplied_usd_and_unpriced_tokens_count_zero():
    g = CaseGraph(2000.0)
    g.add_transfers(A, [tx(A, B, 100, unit="USDC", usd=100.0), tx(A, C, 5, unit="MEME")], depth=0)
    assert g.edges[(A, B)]["usd"] == 100.0 and g.edges[(A, C)]["usd"] == 0.0


def test_depth_increases_away_from_center_and_keeps_minimum(graph):
    assert graph.nodes[A]["depth"] == 0 and graph.nodes[B]["depth"] == 1
    graph.ensure(B, depth=0)
    assert graph.nodes[B]["depth"] == 0
    graph.ensure(B, depth=3)
    assert graph.nodes[B]["depth"] == 0


def test_frontier_excludes_expanded_and_contracts_and_sorts_by_value(graph):
    graph.nodes[A]["expanded"] = True
    graph.ensure(C, {"contract": True})
    assert [f["address"] for f in graph.frontier()] == [B]


def test_to_json_is_serialisable(graph):
    import json
    json.dumps(graph.to_json())
