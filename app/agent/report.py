from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _section(title: str, result: dict[str, Any] | None, empty_note: str) -> list[str]:
    lines = [f"## {title}"]
    if not result:
        lines.append(f"_{empty_note}_")
        lines.append("")
        return lines

    if result["status"] != "ok":
        lines.append(f"_Unavailable: {result.get('error', 'unknown error')}. The research continued without this evidence._")
        lines.append("")
        return lines

    if result.get("is_mock"):
        lines.append("_Demo/mock data - no live source was configured for this tool._")

    for fact in result.get("key_facts", []):
        lines.append(f"- {fact}")

    for lim in result.get("limitations", []):
        lines.append(f"  - *Limitation:* {lim}")

    lines.append("")
    return lines


def build_report_markdown(state: dict[str, Any]) -> str:
    intent = state["intent"]
    normalized: dict[str, dict] = state.get("normalized", {})
    synthesis = state["synthesis"]
    tool_input = state["tool_input"]
    location_label = tool_input["location_label"]
    now = datetime.now(timezone.utc).isoformat()

    lines: list[str] = []
    lines.append(f"# Noida Research Report: {location_label}")
    lines.append("")
    lines.append(f"**Query:** {state['input_text']}  ")
    lines.append(f"**Mode:** {state['mode']}  ")
    lines.append(f"**Report generated:** {now}  ")
    lines.append(f"**Research coverage:** {', '.join(normalized.keys()) or 'none'}")
    lines.append("")

    lines.append("## Executive Summary")
    lines.append(synthesis["executive_summary"])
    lines.append("")

    lines.extend(_section("Latest News and Developments", normalized.get("news"), "News tool was not called for this request."))
    lines.extend(_section("Weather Snapshot", normalized.get("weather"), "Weather tool was not called for this request."))
    lines.extend(_section("Traffic and Connectivity", normalized.get("traffic"), "Traffic tool was not called for this request."))

    lines.append("## Area Insights")
    lines.append(synthesis["area_insights"])
    lines.append("")

    lines.append("## Conclusion")
    lines.append(synthesis["conclusion"])
    lines.append("")

    caveats = list(synthesis.get("caveats", []))
    failed = [name for name, r in normalized.items() if r.get("status") == "failed"]
    if failed:
        caveats.append(f"The following tools failed and are excluded from the evidence above: {', '.join(failed)}.")
    if caveats:
        lines.append("**Caveats:**")
        for c in caveats:
            lines.append(f"- {c}")
        lines.append("")

    lines.append("## Sources")
    for name, result in normalized.items():
        if result.get("status") == "ok" and result.get("source"):
            lines.append(f"- **{name}**: {result['source']} (retrieved {result.get('retrieval_time', 'n/a')})")
    news = normalized.get("news")
    if news and news.get("status") == "ok" and news.get("raw"):
        for item in news["raw"].get("items", []):
            if item.get("url"):
                lines.append(f"  - [{item['headline']}]({item['url']})")
    lines.append("")
    lines.append(f"_Run ID: {state['run_id']}_")

    return "\n".join(lines)
