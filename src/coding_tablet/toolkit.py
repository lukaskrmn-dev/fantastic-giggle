"""High-level toolkit facade for model integrations."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .browser import BrowserSession
from .email_client import DraftEmail
from .network import NetworkPlan
from .registry import RiskLevel, ToolRegistry, ToolSpec
from .notepad import Notepad
from .os_profiles import OSProfile, get_profile
from .shell import ShellAdapter
from .swarm import SwarmPlan
from .session import SessionRuntime


@dataclass(slots=True)
class CodingTablet:
    """Bundle the default tools behind one small-model-friendly object."""

    workspace: Path = Path(".coding-tablet")
    allow_shell: bool = False
    os_profile_name: str = "linux"
    browser: BrowserSession = field(default_factory=BrowserSession)

    @property
    def os_profile(self) -> OSProfile:
        return get_profile(self.os_profile_name)

    @property
    def shell(self) -> ShellAdapter:
        return ShellAdapter(allow_execution=self.allow_shell)

    @property
    def notepad(self) -> Notepad:
        return Notepad(self.workspace)

    def draft_email(self, to: list[str], subject: str, body: str, cc: list[str] | None = None):
        return DraftEmail(to=to, cc=cc or [], subject=subject, body=body).preview()

    def network_preview(self, dns: list[str] | None = None, ipv4: str | None = None, ipv6: str | None = None, gateway: str | None = None):
        return NetworkPlan(dns_servers=dns or [], ipv4=ipv4, ipv6=ipv6, gateway=gateway).preview()

    def plan_swarm(self, goal: str) -> SwarmPlan:
        plan = SwarmPlan(goal)
        plan.add_role("operator", "Use computer tools and report observations.", ("shell", "browser", "notepad"))
        plan.add_role("reviewer", "Check safety, completeness, and final output.", ("notepad",))
        return plan


    def registry(self) -> ToolRegistry:
        registry = ToolRegistry()
        registry.register(
            ToolSpec(
                "shell.run",
                "Run a shell command.",
                RiskLevel.MEDIUM,
                {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"], "additionalProperties": False},
                requires_approval=True,
            ),
            lambda command: self.shell.run(command),
        )
        registry.register(
            ToolSpec(
                "browser.open",
                "Open a web page and extract text and links.",
                RiskLevel.LOW,
                {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"], "additionalProperties": False},
            ),
            lambda url: self.browser.open(url),
        )
        registry.register(
            ToolSpec(
                "notepad.write",
                "Write text inside the workspace.",
                RiskLevel.LOW,
                {"type": "object", "properties": {"name": {"type": "string"}, "text": {"type": "string"}}, "required": ["name", "text"], "additionalProperties": False},
            ),
            lambda name, text: self.notepad.write(name, text),
        )
        registry.register(
            ToolSpec(
                "network.preview",
                "Preview DNS/IP configuration.",
                RiskLevel.HIGH,
                {"type": "object", "properties": {"dns": {"type": "array"}, "ipv4": {"type": "string"}, "ipv6": {"type": "string"}, "gateway": {"type": "string"}}, "additionalProperties": False},
                requires_approval=True,
            ),
            lambda dns=None, ipv4=None, ipv6=None, gateway=None: self.network_preview(dns, ipv4, ipv6, gateway),
        )
        return registry

    def session(self, session_id: str | None = None) -> SessionRuntime:
        return SessionRuntime(self.registry(), self.workspace, session_id=session_id)
