"""ToolAdapter base interface — Integration P0."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any


class AdapterStatus(str, Enum):
    READY = "ready"
    NOT_CONFIGURED = "not_configured"
    ERROR = "error"


class ToolAdapter(ABC):
    name: str
    description: str
    source_project: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]

    @abstractmethod
    async def validate_input(self, params: dict[str, Any]) -> tuple[bool, str | None]:
        ...

    @abstractmethod
    async def run(
        self,
        params: dict[str, Any],
        *,
        dry_run: bool = True,
        timeout: float = 30.0,
    ) -> dict[str, Any]:
        ...

    @abstractmethod
    async def health_check(self) -> AdapterStatus:
        ...
