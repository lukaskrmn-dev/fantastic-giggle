"""Compatibility wrapper for text web browsing."""

from __future__ import annotations

from .actions import Observation
from .browser import BrowserSession


def open_page(url: str, *, timeout_seconds: int = 15, max_chars: int = 4000) -> Observation:
    """Fetch a URL and return visible text plus response metadata."""

    return BrowserSession(timeout_seconds=timeout_seconds, max_chars=max_chars).open(url)
