"""Small interfaces for local and OpenAI-compatible model runtimes."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol
from urllib.request import Request, urlopen


class ModelClient(Protocol):
    def complete(self, messages: list[dict[str, str]]) -> str: ...


@dataclass(slots=True)
class OpenAICompatibleClient:
    """Minimal chat-completions client for local OpenAI-compatible servers."""

    base_url: str
    model: str
    api_key: str = "local"
    timeout_seconds: int = 60

    def complete(self, messages: list[dict[str, str]]) -> str:
        payload = json.dumps({"model": self.model, "messages": messages}).encode()
        request = Request(
            f"{self.base_url.rstrip('/')}/chat/completions",
            data=payload,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=self.timeout_seconds) as response:  # noqa: S310 - configured local/model endpoint
            data = json.loads(response.read().decode())
        return data["choices"][0]["message"]["content"]


@dataclass(slots=True)
class OllamaClient:
    """Minimal Ollama chat client."""

    model: str
    base_url: str = "http://localhost:11434/api"
    timeout_seconds: int = 60

    def complete(self, messages: list[dict[str, str]]) -> str:
        payload = json.dumps({"model": self.model, "messages": messages, "stream": False}).encode()
        request = Request(
            f"{self.base_url.rstrip('/')}/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=self.timeout_seconds) as response:  # noqa: S310 - configured local/model endpoint
            data = json.loads(response.read().decode())
        return data["message"]["content"]
