from __future__ import annotations

from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class ResearchMode(str, Enum):
    QUERY = "query"
    SECTOR = "sector"
    CITY = "city"


class ResearchRequest(BaseModel):
    mode: ResearchMode
    input_text: str = Field(min_length=1, max_length=500)


class IntentExtraction(BaseModel):
    """LLM-facing extraction schema (no geocoding fields - those are computed deterministically)."""

    city: str = "Noida"
    sector: Optional[str] = None
    topic: str
    time_sensitivity: Literal["current", "historical", "general"] = "current"
    constraints: list[str] = Field(default_factory=list)


class SynthesisOutput(BaseModel):
    executive_summary: str
    area_insights: str
    conclusion: str
    caveats: list[str] = Field(default_factory=list)


class ParsedIntent(BaseModel):
    city: str = "Noida"
    sector: Optional[str] = None
    topic: str
    time_sensitivity: Literal["current", "historical", "general"] = "current"
    constraints: list[str] = Field(default_factory=list)
    lat: Optional[float] = None
    lon: Optional[float] = None
    location_label: str


class ResearchPlan(BaseModel):
    questions: list[str]
    tools_to_call: list[str]
    rationale: str


# ---- Tool contracts (input/output schemas used by the harness registry) ----


class ToolInput(BaseModel):
    location_label: str
    city: str
    sector: Optional[str] = None
    topic: str
    lat: Optional[float] = None
    lon: Optional[float] = None
    location_coverage_note: Optional[str] = None


class NewsItem(BaseModel):
    headline: str
    summary: str
    published_at: Optional[str] = None
    source: str
    url: Optional[str] = None
    relevance: str


class NewsToolOutput(BaseModel):
    items: list[NewsItem]
    retrieval_time: str
    coverage: str
    limitations: list[str] = Field(default_factory=list)
    is_mock: bool = False


class WeatherToolOutput(BaseModel):
    location: str
    retrieval_time: str
    conditions: str
    temperature_c: Optional[float] = None
    precipitation_probability: Optional[str] = None
    forecast_note: Optional[str] = None
    source: str
    coverage_note: Optional[str] = None
    is_mock: bool = False


class TrafficToolOutput(BaseModel):
    area: str
    retrieval_time: str
    congestion_level: str
    incidents: list[str] = Field(default_factory=list)
    travel_time_note: Optional[str] = None
    source: str
    limitations: list[str] = Field(default_factory=list)
    is_mock: bool = False


class NormalizedResult(BaseModel):
    tool_name: str
    status: Literal["ok", "failed", "skipped"]
    source: Optional[str] = None
    retrieval_time: Optional[str] = None
    coverage: Optional[str] = None
    key_facts: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    is_mock: bool = False
    error: Optional[str] = None
    raw: Optional[dict[str, Any]] = None


class RunLogEntry(BaseModel):
    run_id: str
    stage: str
    status: Literal["start", "ok", "failed"]
    duration_ms: Optional[float] = None
    detail: Optional[str] = None
