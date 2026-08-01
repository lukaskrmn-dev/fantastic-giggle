"""Browser-like text session for agents that cannot drive a GUI yet."""

from __future__ import annotations

from dataclasses import dataclass, field
from html.parser import HTMLParser
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from .actions import Observation


class _ReadablePageParser(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__()
        self.base_url = base_url
        self.parts: list[str] = []
        self.links: list[dict[str, str]] = []
        self._current_href: str | None = None
        self._current_text: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript"}:
            self._skip_depth += 1
            return
        if tag == "a":
            attrs_dict = dict(attrs)
            href = attrs_dict.get("href")
            self._current_href = urljoin(self.base_url, href) if href else None
            self._current_text = []

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self._skip_depth:
            self._skip_depth -= 1
            return
        if tag == "a" and self._current_href:
            text = " ".join(" ".join(self._current_text).split())
            self.links.append({"text": text or self._current_href, "url": self._current_href})
            self._current_href = None
            self._current_text = []

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        cleaned = " ".join(data.split())
        if not cleaned:
            return
        self.parts.append(cleaned)
        if self._current_href:
            self._current_text.append(cleaned)


@dataclass(slots=True)
class BrowserSession:
    """A small stateful browsing session with history and extracted links."""

    timeout_seconds: int = 15
    max_chars: int = 4000
    history: list[str] = field(default_factory=list)
    current_links: list[dict[str, str]] = field(default_factory=list)

    def open(self, url: str) -> Observation:
        request = Request(url, headers={"User-Agent": "coding-tablet/0.1"})
        with urlopen(request, timeout=self.timeout_seconds) as response:  # noqa: S310 - explicit agent browsing primitive
            body = response.read(self.max_chars * 4).decode(response.headers.get_content_charset() or "utf-8", "replace")
            parser = _ReadablePageParser(response.url)
            parser.feed(body)
            self.history.append(response.url)
            self.current_links = parser.links[:50]
            return Observation(
                True,
                "page opened",
                {
                    "url": response.url,
                    "status": response.status,
                    "content_type": response.headers.get_content_type(),
                    "title": parser.parts[0] if parser.parts else "",
                    "text": "\n".join(parser.parts)[: self.max_chars],
                    "links": self.current_links,
                    "history": list(self.history),
                },
            )


    def click_link(self, index: int) -> Observation:
        """Open a previously extracted link by zero-based index."""

        if index < 0 or index >= len(self.current_links):
            return Observation(False, "link index out of range", {"index": index, "available": len(self.current_links)})
        return self.open(self.current_links[index]["url"])

    def back(self) -> Observation:
        """Return to the previous page when history contains one."""

        if len(self.history) < 2:
            return Observation(False, "no previous page", {"history": list(self.history)})
        self.history.pop()
        previous = self.history.pop()
        return self.open(previous)

    def find_text(self, query: str) -> Observation:
        """Search the current page links and history for a text fragment."""

        matches = [link for link in self.current_links if query.lower() in link["text"].lower() or query.lower() in link["url"].lower()]
        return Observation(True, "browser search completed", {"query": query, "matches": matches, "history_matches": [url for url in self.history if query.lower() in url.lower()]})
