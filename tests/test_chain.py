import json

import pytest

from lib import chain


@pytest.mark.parametrize("addr, ok", [
    ("0x" + "a" * 40, True),
    ("0x" + "A" * 40, True),
    ("0x" + "a" * 39, False),
    ("0x" + "g" * 40, False),
    ("a" * 42, False),
    ("", False),
    (None, False),
])
def test_valid_address(addr, ok):
    assert chain.valid_address(addr) is ok


def test_party_lowercases_hash_and_prefers_explorer_name():
    p = chain._party({"hash": "0xABC", "name": "Hot Wallet", "ens_domain_name": "x.eth"})
    assert p["hash"] == "0xabc" and p["name"] == "Hot Wallet" and p["ens"] == "x.eth"


def test_party_handles_missing():
    assert chain._party(None) == {"hash": None}


def test_cached_reads_snapshot_without_network(tmp_path, monkeypatch):
    monkeypatch.setattr(chain, "SNAP", tmp_path)
    calls = []
    monkeypatch.setattr(chain, "fetch_json", lambda url: calls.append(url) or {"items": [1]})
    assert chain._cached("http://x/1") == {"items": [1]}
    assert chain._cached("http://x/1") == {"items": [1]}
    assert len(calls) == 1 and len(list(tmp_path.glob("*.json"))) == 1
    assert json.loads(next(tmp_path.glob("*.json")).read_text()) == {"items": [1]}
