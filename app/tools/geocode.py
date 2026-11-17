from __future__ import annotations

import httpx

from app.harness.errors import TransientToolError

# Noida city center - used as the city-level fallback whenever sector-level
# geocoding is unavailable (sectors are not in public gazetteers).
NOIDA_CENTER = (28.5355, 77.3910)


async def resolve_location(city: str, sector: str | None) -> tuple[float, float, str, str | None]:
    """Resolve (lat, lon, label, coverage_note) for the requested location.

    Tries to geocode a sector-specific query; falls back to the city center
    with a disclosed coverage note when that is not possible (the common
    case for Noida sectors, which public geocoders do not index).
    """
    if sector:
        query = f"Sector {sector}, {city}, India"
        coords = await _geocode(query)
        if coords:
            return coords[0], coords[1], query, None
        return (
            NOIDA_CENTER[0],
            NOIDA_CENTER[1],
            f"Sector {sector}, {city}",
            f"Sector-level geocoding unavailable; using {city} city-level location as the nearest supported coverage.",
        )

    coords = await _geocode(f"{city}, India")
    if coords:
        return coords[0], coords[1], city, None
    return NOIDA_CENTER[0], NOIDA_CENTER[1], city, None


async def _geocode(query: str) -> tuple[float, float] | None:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={"name": query, "count": 1, "language": "en"},
            )
    except httpx.HTTPError as exc:
        raise TransientToolError(f"geocoding request failed: {exc}") from exc

    if resp.status_code >= 500:
        raise TransientToolError(f"geocoding service returned {resp.status_code}")
    if resp.status_code != 200:
        return None

    data = resp.json()
    results = data.get("results") or []
    if not results:
        return None
    top = results[0]
    return float(top["latitude"]), float(top["longitude"])
