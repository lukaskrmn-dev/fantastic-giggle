"""Workspace-limited notepad tools."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .actions import Observation


@dataclass(slots=True)
class Notepad:
    """Read and write text files below a dedicated workspace directory."""

    workspace: Path = Path(".coding-tablet")

    def _resolve(self, name: str) -> Path:
        root = self.workspace.resolve()
        path = (root / name).resolve()
        if root != path and root not in path.parents:
            raise ValueError("note path must stay inside the workspace")
        return path

    def write(self, name: str, text: str) -> Observation:
        path = self._resolve(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return Observation(True, "note written", {"path": str(path), "bytes": len(text.encode())})

    def read(self, name: str) -> Observation:
        path = self._resolve(name)
        text = path.read_text(encoding="utf-8")
        return Observation(True, "note read", {"path": str(path), "text": text})
