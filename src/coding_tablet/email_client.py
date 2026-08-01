"""Local email drafting primitives without sending mail."""

from __future__ import annotations

from dataclasses import dataclass, field
from email.message import EmailMessage

from .actions import Observation


@dataclass(slots=True)
class DraftEmail:
    """A draft email that can be rendered for review before delivery."""

    to: list[str]
    subject: str
    body: str
    cc: list[str] = field(default_factory=list)

    def as_message(self, sender: str = "agent@coding-tablet.local") -> EmailMessage:
        message = EmailMessage()
        message["From"] = sender
        message["To"] = ", ".join(self.to)
        if self.cc:
            message["Cc"] = ", ".join(self.cc)
        message["Subject"] = self.subject
        message.set_content(self.body)
        return message

    def preview(self) -> Observation:
        message = self.as_message()
        return Observation(
            True,
            "email draft preview created",
            {"to": self.to, "cc": self.cc, "subject": self.subject, "body": self.body, "rfc822": message.as_string()},
        )
