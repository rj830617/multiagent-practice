from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.agent.graph import run_research
from app.harness.logging_setup import log_event
from app.schemas import ResearchRequest

app = FastAPI(title="Noida Research Agent")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    with open("static/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())


@app.post("/research")
async def research(request: ResearchRequest) -> dict:
    try:
        final_state = await run_research(request.mode.value, request.input_text)
    except Exception as exc:  # noqa: BLE001 - surface as a clean API error, keep the process alive
        log_event("pipeline", "failed", "n/a", detail=f"{type(exc).__name__}: {exc}")
        raise HTTPException(status_code=502, detail=f"Research pipeline failed: {exc}") from exc

    return {
        "run_id": final_state["run_id"],
        "mode": final_state["mode"],
        "location_label": final_state["tool_input"]["location_label"],
        "lat": final_state["tool_input"]["lat"],
        "lon": final_state["tool_input"]["lon"],
        "report_markdown": final_state["report_markdown"],
        "normalized": final_state["normalized"],
        "errors": final_state.get("errors", []),
    }


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
