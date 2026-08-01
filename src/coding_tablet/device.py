"""Virtual device actions for future GUI and operating-system adapters."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .actions import Observation


class DeviceActionType(StrEnum):
    CLICK = "click"
    TYPE_TEXT = "type_text"
    HOTKEY = "hotkey"
    WAIT = "wait"
    SCREENSHOT = "screenshot"


@dataclass(frozen=True, slots=True)
class DeviceAction:
    """A normalized GUI action that can target Linux, Windows, macOS, or ChromeOS."""

    action_type: DeviceActionType
    target: str | None = None
    value: str | None = None

    def preview(self) -> Observation:
        return Observation(
            True,
            "device action preview created",
            {"action_type": self.action_type.value, "target": self.target, "value": self.value, "mode": "dry-run"},
        )
