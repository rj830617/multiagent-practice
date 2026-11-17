from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable

from pydantic import BaseModel

from app.schemas import NormalizedResult, ToolInput


@dataclass(frozen=True)
class ToolSpec:
    name: str
    purpose: str
    input_schema: type[BaseModel]
    output_schema: type[BaseModel]
    run_fn: Callable[[ToolInput], Awaitable[BaseModel]]
    normalize_fn: Callable[[BaseModel], NormalizedResult]
    timeout_s: float = 8.0
    max_retries: int = 2


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        if spec.name in self._tools:
            raise ValueError(f"Tool '{spec.name}' is already registered")
        self._tools[spec.name] = spec

    def get(self, name: str) -> ToolSpec:
        if name not in self._tools:
            raise KeyError(f"Unknown tool '{name}'. Registered tools: {list(self._tools)}")
        return self._tools[name]

    def names(self) -> list[str]:
        return list(self._tools.keys())
