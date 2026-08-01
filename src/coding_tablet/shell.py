"""Shell execution adapter with explicit opt-in and command policy."""

from __future__ import annotations

import platform
import subprocess
from dataclasses import dataclass, field

from .actions import Observation


@dataclass(frozen=True, slots=True)
class ShellPolicy:
    """Simple command policy for high-risk shell execution."""

    allowed_prefixes: tuple[str, ...] = ()
    blocked_patterns: tuple[str, ...] = ("rm -rf", "mkfs", "shutdown", "reboot", ":(){ :|:& };:")
    max_output_chars: int = 20_000

    def check(self, command: str) -> str | None:
        lowered = command.lower()
        for pattern in self.blocked_patterns:
            if pattern.lower() in lowered:
                return f"command blocked by policy pattern: {pattern}"
        if self.allowed_prefixes and not command.startswith(self.allowed_prefixes):
            return "command does not match any allowed prefix"
        return None


@dataclass(slots=True)
class ShellAdapter:
    """Run commands through the host shell only when allowed."""

    allow_execution: bool = False
    timeout_seconds: int = 30
    policy: ShellPolicy = field(default_factory=ShellPolicy)

    def run(self, command: str) -> Observation:
        if not self.allow_execution:
            return Observation(False, "shell execution is disabled", {"command": command})
        policy_error = self.policy.check(command)
        if policy_error:
            return Observation(False, "shell command blocked", {"command": command, "error": policy_error})

        completed = subprocess.run(
            command,
            shell=True,
            text=True,
            capture_output=True,
            timeout=self.timeout_seconds,
            check=False,
        )
        stdout = completed.stdout[: self.policy.max_output_chars]
        stderr = completed.stderr[: self.policy.max_output_chars]
        return Observation(
            completed.returncode == 0,
            "command completed" if completed.returncode == 0 else "command failed",
            {
                "command": command,
                "returncode": completed.returncode,
                "stdout": stdout,
                "stderr": stderr,
                "truncated": len(completed.stdout) > len(stdout) or len(completed.stderr) > len(stderr),
                "host_os": platform.system(),
            },
        )
