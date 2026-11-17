from __future__ import annotations

from datetime import datetime, timezone

import httpx

from app.config import settings
from app.harness.errors import TransientToolError, ToolInputError
from app.schemas import NormalizedResult, ToolInput, WeatherToolOutput

_WMO_CODES = {
    0: "clear sky", 1: "mainly clear", 2: "partly cloudy", 3: "overcast",
    45: "fog", 48: "freezing fog",
    51: "light drizzle", 53: "moderate drizzle", 55: "dense drizzle",
    61: "light rain", 63: "moderate rain", 65: "heavy rain",
    71: "light snow", 73: "moderate snow", 75: "heavy snow",
    80: "light rain showers", 81: "moderate rain showers", 82: "violent rain showers",
    95: "thunderstorm", 96: "thunderstorm with hail", 99: "thunderstorm with heavy hail",
}


async def run(tool_input: ToolInput) -> WeatherToolOutput:
    if tool_input.lat is None or tool_input.lon is None:
        raise ToolInputError("resolved lat/lon is required for the weather tool")

    lat, lon, label, coverage_note = (
        tool_input.lat,
        tool_input.lon,
        tool_input.location_label,
        tool_input.location_coverage_note,
    )

    if settings.openweather_api_key:
        return await _run_openweathermap(lat, lon, label, coverage_note)
    return await _run_open_meteo(lat, lon, label, coverage_note)


async def _run_open_meteo(lat: float, lon: float, label: str, coverage_note: str | None) -> WeatherToolOutput:
    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            resp = await client.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "current": "temperature_2m,precipitation,weather_code",
                    "daily": "precipitation_probability_max,temperature_2m_max,temperature_2m_min,weather_code",
                    "timezone": "Asia/Kolkata",
                    "forecast_days": 2,
                },
            )
    except httpx.HTTPError as exc:
        raise TransientToolError(f"Open-Meteo request failed: {exc}") from exc

    if resp.status_code >= 500:
        raise TransientToolError(f"Open-Meteo returned {resp.status_code}")
    if resp.status_code != 200:
        raise ToolInputError(f"Open-Meteo rejected request: {resp.status_code} {resp.text[:200]}")

    data = resp.json()
    current = data.get("current", {})
    daily = data.get("daily", {})

    code = current.get("weather_code")
    conditions = _WMO_CODES.get(code, "unknown")

    tomorrow_note = None
    try:
        tmax = daily["temperature_2m_max"][1]
        tmin = daily["temperature_2m_min"][1]
        pprob = daily["precipitation_probability_max"][1]
        tomorrow_code = daily["weather_code"][1]
        tomorrow_note = (
            f"Tomorrow: {_WMO_CODES.get(tomorrow_code, 'unknown')}, {tmin}-{tmax} C, "
            f"precipitation probability {pprob}%"
        )
    except (KeyError, IndexError):
        pass

    return WeatherToolOutput(
        location=label,
        retrieval_time=datetime.now(timezone.utc).isoformat(),
        conditions=conditions,
        temperature_c=current.get("temperature_2m"),
        precipitation_probability=f"{daily.get('precipitation_probability_max', [None])[0]}%"
        if daily.get("precipitation_probability_max")
        else None,
        forecast_note=tomorrow_note,
        source="Open-Meteo (open-meteo.com), no API key required",
        coverage_note=coverage_note,
        is_mock=False,
    )


async def _run_openweathermap(lat: float, lon: float, label: str, coverage_note: str | None) -> WeatherToolOutput:
    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            resp = await client.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={"lat": lat, "lon": lon, "appid": settings.openweather_api_key, "units": "metric"},
            )
    except httpx.HTTPError as exc:
        raise TransientToolError(f"OpenWeatherMap request failed: {exc}") from exc

    if resp.status_code >= 500 or resp.status_code == 429:
        raise TransientToolError(f"OpenWeatherMap returned {resp.status_code}")
    if resp.status_code != 200:
        raise ToolInputError(f"OpenWeatherMap rejected request: {resp.status_code}")

    data = resp.json()
    weather = (data.get("weather") or [{}])[0]
    main = data.get("main", {})

    return WeatherToolOutput(
        location=label,
        retrieval_time=datetime.now(timezone.utc).isoformat(),
        conditions=weather.get("description", "unknown"),
        temperature_c=main.get("temp"),
        precipitation_probability=None,
        forecast_note="Short-term forecast not requested in this call (current conditions only).",
        source="OpenWeatherMap",
        coverage_note=coverage_note,
        is_mock=False,
    )


def normalize(output: WeatherToolOutput) -> NormalizedResult:
    key_facts = [f"Conditions: {output.conditions}"]
    if output.temperature_c is not None:
        key_facts.append(f"Temperature: {output.temperature_c} C")
    if output.precipitation_probability:
        key_facts.append(f"Precipitation probability: {output.precipitation_probability}")
    if output.forecast_note:
        key_facts.append(output.forecast_note)

    limitations = [output.coverage_note] if output.coverage_note else []

    return NormalizedResult(
        tool_name="weather",
        status="ok",
        source=output.source,
        retrieval_time=output.retrieval_time,
        coverage=output.location,
        key_facts=key_facts,
        limitations=limitations,
        is_mock=output.is_mock,
        raw=output.model_dump(),
    )
