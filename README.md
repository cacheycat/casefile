# Casefile

A budgeted on-chain investigation agent that cites its evidence.

Give it an Ethereum address. It expands the fund-flow graph under a fixed budget of fetches,
scores entities with computed features, and writes a case file in which every claim points at
transactions the code actually saw.

## Design

- **Facts are computed, claims are modelled.** Counterparties, volumes, fan-in/fan-out and
  timing come from `CaseGraph`; the model only interprets them and must cite edges.
- **Untrusted strings.** Token names, ENS labels and tags from the chain are adversarial
  input. They are fenced in prompts and can never add an address to the fetch queue, so a
  scam token cannot steer the investigation.
- **Budgeted loop.** `Plan -> Expand -> Score -> Decide -> Report`, bounded in steps and
  fetches. A node budget caps what the UI draws.
- **RAG.** Typology cards (`knowledge/`) on laundering patterns, scam surfaces and
  investigation craft, retrieved by hybrid BM25 + TF-IDF.
- **Memory.** Heuristics from past cases are stored and ranked by learned utility.
- **Reproducible.** Blockscout responses are snapshotted on disk, so a case can be replayed
  offline.

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt          # needs git access to cacheycat/agentkit
python app.py                            # http://localhost:8812
```

Working on both repos at once? Link a sibling checkout instead of installing it:

```bash
pip install fastapi uvicorn numpy certifi pydantic
ln -s ../agentkit/agentkit agentkit      # ignored by git
```

The LLM layer uses `ANTHROPIC_API_KEY`, else a local headless `claude` CLI with tools
disabled, else a deterministic heuristic report.

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/meta` | Provider mode, budgets, example addresses |
| POST | `/api/case` | Open a case for an address |
| GET | `/api/memory` | Stored heuristics with learned utility |
| GET | `/api/runs`, `/api/runs/{id}`, `/api/runs/{id}/events` | Run list, detail, SSE trace |

## Tests

```bash
pip install -r requirements-dev.txt
pytest -q && ruff check .
```
