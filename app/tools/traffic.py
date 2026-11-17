from __future__ import annotations

from datetime import datetime, timezone

import httpx

from app.config import settings
from app.harness.errors import ToolInputError, TransientToolError
from app.schemas import NormalizedResult, ToolInput, TrafficToolOutput

_KNOWN_CONNECTIVITY = (
    "Noida's primary arteries include the DND Flyway, Noida-Greater Noida Expressway, "
    "FNG Expressway, and the Noida-Greater Noida Link Road. Metro connectivity is via the "
    "Delhi Metro Blue Line and the Aqua Line (Noida-Greater Noida Metro)."
)


async def run(tool_input: ToolInput) -> TrafficToolOutput:
    if tool_input.lat is None or tool_input.lon is None:
        raise ToolInputError("resolved lat/lon is required for the traffic tool")

    lat, lon, label, coverage_note = (
        tool_input.lat,
        tool_input.lon,
        tool_input.location_label,
        tool_input.location_coverage_note,
    )

    if settings.tomtom_api_key:
        return await _run_tomtom(lat, lon, label, coverage_note)
    return _mock_response(label, coverage_note)


async def _run_tomtom(lat: float, lon: float, label: str, coverage_note: str | None) -> TrafficToolOutput:
    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            resp = await client.get(
                "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json",
                params={"point": f"{lat},{lon}", "key": settings.tomtom_api_key},
            )
    except httpx.HTTPError as exc:
        raise TransientToolError(f"TomTom request failed: {exc}") from exc

    if resp.status_code == 429 or resp.status_code >= 500:
        raise TransientToolError(f"TomTom returned {resp.status_code}")
    if resp.status_code != 200:
        raise ToolInputError(f"TomTom rejected request: {resp.status_code} {resp.text[:200]}")

    data = resp.json().get("flowSegmentData", {})
    current_speed = data.get("currentSpeed")
    free_flow_speed = data.get("freeFlowSpeed")

    congestion_level = "unknown"
    travel_time_note = None
    if current_speed is not None and free_flow_speed:
        ratio = current_speed / free_flow_speed
        if ratio >= 0.8:
            congestion_level = "light"
        elif ratio >= 0.5:
            congestion_level = "moderate"
        else:
            congestion_level = "heavy"
        travel_time_note = f"Current speed {current_speed} km/h vs free-flow {free_flow_speed} km/h"

    incidents = []
    if data.get("roadClosure"):
        incidents.append("Road closure reported on this segment.")

    return TrafficToolOutput(
        area=label,
        retrieval_time=datetime.now(timezone.utc).isoformat(),
        congestion_level=congestion_level,
        incidents=incidents,
        travel_time_note=travel_time_note,
        source="TomTom Traffic API",
        limitations=[coverage_note] if coverage_note else [],
        is_mock=False,
    )


def _mock_response(label: str, coverage_note: str | None) -> TrafficToolOutput:
    limitations = [
        "TOMTOM_API_KEY not configured; no live traffic source was queried. "
        "Showing demo/mock congestion data and general connectivity context only."
    ]
    if coverage_note:
        limitations.append(coverage_note)

    return TrafficToolOutput(
        area=label,
        retrieval_time=datetime.now(timezone.utc).isoformat(),
        congestion_level="unknown (mock)",
        incidents=["[DEMO] No live incident feed available."],
        travel_time_note=_KNOWN_CONNECTIVITY,
        source="mock-demo",
        limitations=limitations,
        is_mock=True,
    )


def normalize(output: TrafficToolOutput) -> NormalizedResult:
    key_facts = [f"Congestion level: {output.congestion_level}"]
    if output.travel_time_note:
        key_facts.append(output.travel_time_note)
    key_facts.extend(output.incidents)

    return NormalizedResult(
        tool_name="traffic",
        status="ok",
        source=output.source,
        retrieval_time=output.retrieval_time,
        coverage=output.area,
        key_facts=key_facts,
        limitations=output.limitations,
        is_mock=output.is_mock,
        raw=output.model_dump(),
    )
