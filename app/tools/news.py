from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx

from app.config import settings
from app.harness.errors import ToolInputError, TransientToolError
from app.schemas import NewsItem, NewsToolOutput, NormalizedResult, ToolInput

_STALE_DAYS = 30


async def run(tool_input: ToolInput) -> NewsToolOutput:
    query = _build_query(tool_input)
    if not query.strip():
        raise ToolInputError("news tool requires a non-empty location/topic query")

    if not settings.news_api_key:
        return _mock_response(query)

    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            resp = await client.get(
                "https://newsapi.org/v2/everything",
                params={
                    "q": query,
                    "sortBy": "publishedAt",
                    "language": "en",
                    "pageSize": 5,
                    "apiKey": settings.news_api_key,
                },
            )
    except httpx.HTTPError as exc:
        raise TransientToolError(f"NewsAPI request failed: {exc}") from exc

    if resp.status_code == 429 or resp.status_code >= 500:
        raise TransientToolError(f"NewsAPI returned {resp.status_code}")
    if resp.status_code != 200:
        raise ToolInputError(f"NewsAPI rejected request: {resp.status_code} {resp.text[:200]}")

    data = resp.json()
    articles = data.get("articles") or []

    now = datetime.now(timezone.utc)
    items: list[NewsItem] = []
    stale_count = 0
    for article in articles[:5]:
        published_at = article.get("publishedAt")
        is_stale = False
        if published_at:
            try:
                pub_dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                is_stale = (now - pub_dt) > timedelta(days=_STALE_DAYS)
            except ValueError:
                pass
        if is_stale:
            stale_count += 1
        items.append(
            NewsItem(
                headline=article.get("title") or "(untitled)",
                summary=(article.get("description") or "").strip() or "(no summary provided)",
                published_at=published_at,
                source=(article.get("source") or {}).get("name") or "unknown",
                url=article.get("url"),
                relevance=f"Matched query: '{query}'" + (" (older than 30 days)" if is_stale else ""),
            )
        )

    limitations = []
    if not items:
        limitations.append("No recent news coverage found for this query.")
    elif stale_count == len(items):
        limitations.append("All matched articles are older than 30 days; no recent coverage was found.")

    return NewsToolOutput(
        items=items,
        retrieval_time=now.isoformat(),
        coverage=query,
        limitations=limitations,
        is_mock=False,
    )


def _build_query(tool_input: ToolInput) -> str:
    parts = [tool_input.city]
    if tool_input.sector:
        parts.append(f"Sector {tool_input.sector}")
    if tool_input.topic and tool_input.topic.lower() not in {"general overview", "overview", ""}:
        parts.append(tool_input.topic)
    return " ".join(p for p in parts if p)


def _mock_response(query: str) -> NewsToolOutput:
    now = datetime.now(timezone.utc)
    return NewsToolOutput(
        items=[
            NewsItem(
                headline=f"[DEMO] Infrastructure update referencing {query}",
                summary=(
                    "This is a clearly-labelled mock article used for demonstration because no "
                    "NEWS_API_KEY is configured. No live news source was queried."
                ),
                published_at=None,
                source="mock-demo",
                url=None,
                relevance="Demo placeholder only - not a real retrieval.",
            )
        ],
        retrieval_time=now.isoformat(),
        coverage=query,
        limitations=["NEWS_API_KEY not configured; showing mock/demo data only, not live news."],
        is_mock=True,
    )


def normalize(output: NewsToolOutput) -> NormalizedResult:
    key_facts = [
        f"{item.headline} ({item.published_at or 'date unknown'}) - {item.source}"
        for item in output.items
    ]
    return NormalizedResult(
        tool_name="news",
        status="ok",
        source="NewsAPI.org" if not output.is_mock else "mock-demo",
        retrieval_time=output.retrieval_time,
        coverage=output.coverage,
        key_facts=key_facts,
        limitations=output.limitations,
        is_mock=output.is_mock,
        raw=output.model_dump(),
    )
