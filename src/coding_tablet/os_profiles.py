"""Operating-system profile descriptions for adapters and prompts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal

PathStyle = Literal["posix", "nt", "mixed"]
ShellFamily = Literal["bash", "zsh", "powershell", "cmd", "crosh"]


@dataclass(frozen=True, slots=True)
class OSProfile:
    """A compact description of an operating system persona."""

    name: str
    shell: ShellFamily
    path_style: PathStyle
    package_managers: tuple[str, ...] = field(default_factory=tuple)
    notes: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


OS_PROFILES: dict[str, OSProfile] = {
    "linux": OSProfile("linux", "bash", "posix", ("apt", "dnf", "pacman"), "Common server and desktop Linux profile."),
    "windows-powershell": OSProfile("windows-powershell", "powershell", "nt", ("winget", "choco"), "Modern Windows automation profile."),
    "windows-cmd": OSProfile("windows-cmd", "cmd", "nt", ("winget", "choco"), "Legacy Windows command prompt profile."),
    "macos": OSProfile("macos", "zsh", "posix", ("brew",), "Default macOS terminal profile."),
    "chromeos": OSProfile("chromeos", "crosh", "mixed", ("apt in Linux container",), "ChromeOS shell plus optional Linux container."),
}


def get_profile(name: str) -> OSProfile:
    """Return an OS profile by name with a helpful error for invalid names."""

    try:
        return OS_PROFILES[name]
    except KeyError as exc:
        available = ", ".join(sorted(OS_PROFILES))
        raise ValueError(f"unknown OS profile '{name}'. Available profiles: {available}") from exc
