"""Rebuild demo/snapshots from the live cache.

Runs the baseline investigation for the demo seed, records which Blockscout
responses it read, and writes trimmed copies so a fresh clone works offline.

    AGENT_LLM=baseline python scripts/build_demo.py
"""
import json
import os
import shutil
import sys
from pathlib import Path

os.environ["AGENT_LLM"] = "baseline"
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agentkit import LLM, Memory, Store  # noqa: E402
from lib import agent, chain  # noqa: E402

KEEP_ITEMS = 25
DEMO_SEED = "0xd8da6bf26964af9d7eed9e03e53415d37aa96045"

used: list[Path] = []
_orig = chain._cached


def recording(url: str) -> dict:
    out = _orig(url)
    used.append(chain.SNAP / (chain.hashlib.sha1(url.encode()).hexdigest()[:24] + ".json"))
    return out


chain._cached = recording
store = Store(ROOT / "data" / "build_demo.db")
agent.investigate(lambda *_: None, memory=Memory(store), llm=LLM(provider=None), seed=DEMO_SEED, budget=3)

dest = ROOT / "demo" / "snapshots"
shutil.rmtree(dest, ignore_errors=True)
dest.mkdir(parents=True)
for path in dict.fromkeys(used):
    body = json.loads(path.read_text())
    if isinstance(body, dict) and isinstance(body.get("items"), list):
        body["items"] = body["items"][:KEEP_ITEMS]
        body["next_page_params"] = None
    (dest / path.name).write_text(json.dumps(body, separators=(",", ":")))
print(f"wrote {len(used)} snapshots, {sum(f.stat().st_size for f in dest.iterdir()) // 1024} KiB")
