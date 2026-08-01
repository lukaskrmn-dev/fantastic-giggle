"""Auditable session runtime for plan-act-observe workflows."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .actions import Observation
from .registry import RiskLevel, ToolRegistry, ToolSpec


@dataclass(frozen=True, slots=True)
class ActionRequest:
    tool: str
    input: dict[str, object] = field(default_factory=dict)
    reason: str = ""


@dataclass(frozen=True, slots=True)
class ApprovalRequest:
    action: ActionRequest
    risk: RiskLevel
    message: str


@dataclass(slots=True)
class SessionEvent:
    event_id: str
    session_id: str
    phase: str
    payload: dict[str, object]
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class SessionRuntime:
    """Run approved tool calls and persist a JSONL trace."""

    def __init__(self, registry: ToolRegistry, workspace: Path = Path(".coding-tablet"), session_id: str | None = None) -> None:
        self.registry = registry
        self.session_id = session_id or f"session-{uuid4().hex[:12]}"
        self.root = workspace / "sessions" / self.session_id
        self.trace_path = self.root / "trace.jsonl"
        self.events: list[SessionEvent] = []

    def start(self, goal: str) -> Observation:
        self.root.mkdir(parents=True, exist_ok=True)
        self._record("start", {"goal": goal, "tools": self.registry.specs()})
        return Observation(True, "session started", {"session_id": self.session_id, "trace_path": str(self.trace_path)})

    def request(self, action: ActionRequest, *, approved: bool = False) -> Observation:
        registered = self.registry.get(action.tool)
        spec = registered.spec
        if spec.requires_approval and not approved:
            approval = ApprovalRequest(action, spec.risk, f"approval required for {action.tool}")
            self._record("approval_required", {"approval": self._approval_to_dict(approval)})
            return Observation(False, "approval required", self._approval_to_dict(approval))

        self._record("act", {"tool": action.tool, "input": action.input, "reason": action.reason})
        result = self.registry.call(action.tool, **action.input)
        self._record("observe", result.to_dict())
        return result

    def _record(self, phase: str, payload: dict[str, object]) -> None:
        event = SessionEvent(f"event-{len(self.events) + 1}", self.session_id, phase, payload)
        self.events.append(event)
        self.root.mkdir(parents=True, exist_ok=True)
        with self.trace_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(event.to_dict(), sort_keys=True) + "\n")

    @staticmethod
    def _approval_to_dict(approval: ApprovalRequest) -> dict[str, object]:
        return {
            "action": {"tool": approval.action.tool, "input": approval.action.input, "reason": approval.action.reason},
            "risk": approval.risk.value,
            "message": approval.message,
        }
