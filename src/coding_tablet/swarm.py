"""Lightweight task swarm planner inspired by modern computer-use agents."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from .actions import Observation


class TaskStatus(StrEnum):
    """Lifecycle states for a small-model-friendly task graph."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass(slots=True)
class AgentRole:
    """A narrow worker role that can be assigned to a small model or tool adapter."""

    name: str
    purpose: str
    tools: tuple[str, ...] = field(default_factory=tuple)


@dataclass(slots=True)
class TaskStep:
    """One auditable step in a larger computer-use task."""

    id: str
    instruction: str
    role: str = "operator"
    status: TaskStatus = TaskStatus.PENDING
    depends_on: tuple[str, ...] = field(default_factory=tuple)


@dataclass(slots=True)
class SwarmPlan:
    """A deterministic plan for coordinating multiple small specialized agents."""

    goal: str
    roles: list[AgentRole] = field(default_factory=list)
    steps: list[TaskStep] = field(default_factory=list)

    def add_role(self, name: str, purpose: str, tools: tuple[str, ...] = ()) -> AgentRole:
        role = AgentRole(name=name, purpose=purpose, tools=tools)
        self.roles.append(role)
        return role

    def add_step(self, instruction: str, *, role: str = "operator", depends_on: tuple[str, ...] = ()) -> TaskStep:
        step = TaskStep(id=f"step-{len(self.steps) + 1}", instruction=instruction, role=role, depends_on=depends_on)
        self.steps.append(step)
        return step

    def next_ready_steps(self) -> list[TaskStep]:
        complete_ids = {step.id for step in self.steps if step.status == TaskStatus.COMPLETE}
        return [
            step
            for step in self.steps
            if step.status == TaskStatus.PENDING and all(dependency in complete_ids for dependency in step.depends_on)
        ]

    def preview(self) -> Observation:
        return Observation(
            True,
            "swarm plan preview created",
            {
                "goal": self.goal,
                "roles": [{"name": role.name, "purpose": role.purpose, "tools": list(role.tools)} for role in self.roles],
                "steps": [
                    {
                        "id": step.id,
                        "instruction": step.instruction,
                        "role": step.role,
                        "status": step.status.value,
                        "depends_on": list(step.depends_on),
                    }
                    for step in self.steps
                ],
                "ready": [step.id for step in self.next_ready_steps()],
            },
        )
