"""The committed demo snapshot lets the baseline investigation run with no network."""
import pytest
from agentkit import LLM, Memory, Store

from lib import agent, chain

DEMO_SEED = "0xd8da6bf26964af9d7eed9e03e53415d37aa96045"


@pytest.fixture()
def offline(tmp_path, monkeypatch):
    monkeypatch.setattr(chain, "SNAP", tmp_path / "empty")

    def no_network(url):
        raise AssertionError(f"unexpected network call: {url}")

    monkeypatch.setattr(chain, "fetch_json", no_network)


def test_baseline_investigation_replays_from_demo_snapshot(offline, tmp_path):
    events = []
    out = agent.investigate(lambda t, p: events.append(t), memory=Memory(Store(tmp_path / "m.db")),
                            llm=LLM(provider=None), seed=DEMO_SEED, budget=3)
    assert out["report"] and out["graph_json"]["nodes"]
    assert "node_start" in events
