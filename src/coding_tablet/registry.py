"""Tool registry and risk metadata for model-facing integrations."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any, Callable

from .actions import Observation


class RiskLevel(StrEnum):
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True, slots=True)
class ToolSpec:
    name: str
    description: str
    risk: RiskLevel = RiskLevel.LOW
    input_schema: dict[str, Any] = field(default_factory=dict)
    requires_approval: bool = False

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["risk"] = self.risk.value
        return data


@dataclass(slots=True)
class RegisteredTool:
    spec: ToolSpec
    handler: Callable[..., Observation]


class ToolRegistry:
    """A small explicit registry so models can discover tools safely."""

    def __init__(self) -> None:
        self._tools: dict[str, RegisteredTool] = {}

    def register(self, spec: ToolSpec, handler: Callable[..., Observation]) -> None:
        if spec.name in self._tools:
            raise ValueError(f"tool already registered: {spec.name}")
        self._tools[spec.name] = RegisteredTool(spec, handler)

    def specs(self) -> list[dict[str, Any]]:
        return [tool.spec.to_dict() for tool in self._tools.values()]

    def get(self, name: str) -> RegisteredTool:
        try:
            return self._tools[name]
        except KeyError as exc:
            available = ", ".join(sorted(self._tools))
            raise ValueError(f"unknown tool '{name}'. Available tools: {available}") from exc

    def call(self, name: str, **kwargs: Any) -> Observation:
        registered = self.get(name)
        validation_error = validate_input(registered.spec.input_schema, kwargs)
        if validation_error:
            return Observation(False, "invalid tool input", {"tool": name, "error": validation_error})
        return registered.handler(**kwargs)


def validate_input(schema: dict[str, Any], payload: dict[str, Any]) -> str | None:
    """Validate a compact JSON-schema subset used by built-in tools."""

    if not schema:
        return None
    if schema.get("type") != "object":
        return "only object schemas are supported"
    properties: dict[str, Any] = schema.get("properties", {})
    required = set(schema.get("required", []))
    additional = schema.get("additionalProperties", True)

    missing = sorted(required - payload.keys())
    if missing:
        return f"missing required fields: {', '.join(missing)}"
    if additional is False:
        unknown = sorted(set(payload) - set(properties))
        if unknown:
            return f"unknown fields: {', '.join(unknown)}"
    for key, value in payload.items():
        expected = properties.get(key, {}).get("type")
        if expected and not _matches_type(value, expected):
            return f"field '{key}' must be {expected}"
    return None


def _matches_type(value: Any, expected: str) -> bool:
    if expected == "string":
        return isinstance(value, str)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, int | float) and not isinstance(value, bool)
    if expected == "array":
        return isinstance(value, list)
    if expected == "object":
        return isinstance(value, dict)
    return True
