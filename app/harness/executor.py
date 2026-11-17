from __future__ import annotations

import asyncio
import time

from pydantic import ValidationError

from app.harness.errors import ToolInputError, TransientToolError
from app.harness.logging_setup import log_event
from app.harness.registry import ToolRegistry, ToolSpec
from app.schemas import NormalizedResult, ToolInput


async def run_tool(spec: ToolSpec, tool_input: ToolInput, run_id: str) -> NormalizedResult:
    """Execute one registered tool with validation, timeout and bounded retries.

    Never raises: failures are captured as a NormalizedResult(status="failed")
    so the orchestration can continue with partial results.
    """
    try:
        spec.input_schema.model_validate(tool_input.model_dump())
    except ValidationError as exc:
        log_event(spec.name, "failed", run_id, detail=f"input validation error: {exc}")
        return NormalizedResult(tool_name=spec.name, status="failed", error="invalid input")

    last_error: str = "unknown error"
    for attempt in range(1, spec.max_retries + 2):  # first try + retries
        start = time.monotonic()
        log_event(spec.name, "start", run_id, detail=f"attempt {attempt}")
        try:
            raw_output = await asyncio.wait_for(spec.run_fn(tool_input), timeout=spec.timeout_s)
            duration_ms = (time.monotonic() - start) * 1000
            normalized = spec.normalize_fn(raw_output)
            log_event(spec.name, "ok", run_id, duration_ms=duration_ms)
            return normalized
        except asyncio.TimeoutError:
            last_error = f"timed out after {spec.timeout_s}s"
        except TransientToolError as exc:
            last_error = str(exc)
        except ToolInputError as exc:
            log_event(spec.name, "failed", run_id, detail=str(exc))
            return NormalizedResult(tool_name=spec.name, status="failed", error=str(exc))
        except Exception as exc:  # noqa: BLE001 - tool failures must not crash the pipeline
            last_error = f"{type(exc).__name__}: {exc}"
            log_event(spec.name, "failed", run_id, detail=f"attempt {attempt} error: {last_error}")
            # Unexpected errors are not retried.
            return NormalizedResult(tool_name=spec.name, status="failed", error=last_error)

        duration_ms = (time.monotonic() - start) * 1000
        log_event(spec.name, "failed", run_id, duration_ms=duration_ms, detail=f"attempt {attempt}: {last_error}")
        if attempt <= spec.max_retries:
            await asyncio.sleep(min(2 ** (attempt - 1) * 0.5, 4.0))

    return NormalizedResult(tool_name=spec.name, status="failed", error=last_error)


async def run_tools(registry: ToolRegistry, tool_names: list[str], tool_input: ToolInput, run_id: str) -> dict[str, NormalizedResult]:
    """Run the requested tools in parallel (they are independent) and collect results."""
    specs = [registry.get(name) for name in tool_names]
    results = await asyncio.gather(*(run_tool(spec, tool_input, run_id) for spec in specs))
    return {spec.name: result for spec, result in zip(specs, results)}
