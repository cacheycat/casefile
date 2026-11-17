"""Casefile: a budgeted on-chain investigation agent. Run with `python app.py`."""
from __future__ import annotations

from pathlib import Path

import uvicorn
from fastapi import HTTPException
from pydantic import BaseModel, Field

from agentkit import LLM, Memory, Runner, Store
from agentkit.serve import make_app
from lib import agent, chain

ROOT = Path(__file__).parent
store = Store(ROOT / "data" / "casefile.db")
memory = Memory(store)
runner = Runner(store)
app = make_app("Casefile", ROOT / "web", store, runner)

# A seed with public attribution, used as the out-of-the-box demo case.
DEMO_SEED = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045".lower()


class CaseIn(BaseModel):
    seed: str
    budget: int = Field(6, ge=2, le=10)
    per_round: int = Field(2, ge=1, le=3)
    note: str = Field("", max_length=300)


@app.get("/api/meta")
def meta():
    llm = LLM()
    return {"mode": llm.mode, "model": llm.model, "graph": agent.describe_graph(),
            "demo_seed": DEMO_SEED, "busy": runner.busy("case"),
            "knowledge_passages": len(agent.CARDS.docs)}


@app.post("/api/case")
def start_case(body: CaseIn):
    seed = body.seed.strip().lower()
    if not chain.valid_address(seed):
        raise HTTPException(422, "that is not a valid Ethereum address (0x + 40 hex characters)")
    if runner.busy("case"):
        raise HTTPException(409, "an investigation is already in progress")
    llm = LLM()

    def job(run_id, emit):
        return agent.investigate(emit, memory=memory, llm=llm, seed=seed,
                                 budget=body.budget, per_round=body.per_round, case_note=body.note)

    return {"run_id": runner.start("case", f"{seed[:10]}… · budget {body.budget}", body.model_dump(), job)}


@app.get("/api/memory")
def heuristics():
    return memory.all("heuristic")


app.finish()

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8812, log_level="warning")
