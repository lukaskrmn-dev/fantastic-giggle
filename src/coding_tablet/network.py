"""Dry-run network configuration planning."""

from __future__ import annotations

from dataclasses import dataclass, field
from ipaddress import ip_address, ip_interface

from .actions import Observation


@dataclass(slots=True)
class NetworkPlan:
    """Declarative DNS, IPv4, and IPv6 configuration intent."""

    dns_servers: list[str] = field(default_factory=list)
    ipv4: str | None = None
    ipv6: str | None = None
    gateway: str | None = None

    def validate(self) -> list[str]:
        errors: list[str] = []
        for server in self.dns_servers:
            try:
                ip_address(server)
            except ValueError:
                errors.append(f"invalid DNS server IP: {server}")
        for label, value in (("ipv4", self.ipv4), ("ipv6", self.ipv6)):
            if value is None:
                continue
            try:
                interface = ip_interface(value)
            except ValueError:
                errors.append(f"invalid {label} interface: {value}")
                continue
            if label == "ipv4" and interface.version != 4:
                errors.append(f"ipv4 must be an IPv4 interface: {value}")
            if label == "ipv6" and interface.version != 6:
                errors.append(f"ipv6 must be an IPv6 interface: {value}")
        if self.gateway:
            try:
                ip_address(self.gateway)
            except ValueError:
                errors.append(f"invalid gateway IP: {self.gateway}")
        return errors

    def preview(self) -> Observation:
        errors = self.validate()
        return Observation(
            not errors,
            "network configuration preview created" if not errors else "network configuration is invalid",
            {
                "dns_servers": self.dns_servers,
                "ipv4": self.ipv4,
                "ipv6": self.ipv6,
                "gateway": self.gateway,
                "mode": "dry-run",
                "errors": errors,
            },
        )
