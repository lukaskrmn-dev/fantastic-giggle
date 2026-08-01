"""Shared action result types."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(slots=True)
class Observation:
    """A compact result object that small models can parse reliably."""

    ok: bool
    summary: str
    data: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""

        return asdict(self)
