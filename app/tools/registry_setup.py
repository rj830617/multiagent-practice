from app.harness.registry import ToolRegistry, ToolSpec
from app.schemas import NewsToolOutput, ToolInput, TrafficToolOutput, WeatherToolOutput
from app.tools import news, traffic, weather


def build_registry() -> ToolRegistry:
    registry = ToolRegistry()

    registry.register(
        ToolSpec(
            name="news",
            purpose="Find recent news and public announcements about a Noida city/sector/topic.",
            input_schema=ToolInput,
            output_schema=NewsToolOutput,
            run_fn=news.run,
            normalize_fn=news.normalize,
            timeout_s=8.0,
            max_retries=2,
        )
    )
    registry.register(
        ToolSpec(
            name="weather",
            purpose="Retrieve current weather and a short forecast for a Noida location.",
            input_schema=ToolInput,
            output_schema=WeatherToolOutput,
            run_fn=weather.run,
            normalize_fn=weather.normalize,
            timeout_s=6.0,
            max_retries=2,
        )
    )
    registry.register(
        ToolSpec(
            name="traffic",
            purpose="Retrieve traffic/congestion/connectivity information for a Noida location.",
            input_schema=ToolInput,
            output_schema=TrafficToolOutput,
            run_fn=traffic.run,
            normalize_fn=traffic.normalize,
            timeout_s=6.0,
            max_retries=2,
        )
    )
    return registry
