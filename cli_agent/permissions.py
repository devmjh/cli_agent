from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Capability = Literal["read", "write", "shell", "net"]
ALL_CAPABILITIES: tuple[Capability, ...] = ("read", "write", "shell", "net")


@dataclass
class PermissionState:
    defaults: dict[Capability, bool] = field(
        default_factory=lambda: {
            "read": False,
            "write": False,
            "shell": False,
            "net": False,
        }
    )
    session_overrides: dict[Capability, bool | None] = field(
        default_factory=lambda: {
            "read": None,
            "write": None,
            "shell": None,
            "net": None,
        }
    )

    def is_allowed(self, capability: Capability) -> bool:
        override = self.session_overrides[capability]
        if override is not None:
            return override
        return self.defaults[capability]

    def allow(self, capability: Capability) -> None:
        self.session_overrides[capability] = True

    def deny(self, capability: Capability) -> None:
        self.session_overrides[capability] = False

    def reset_overrides(self) -> None:
        for cap in ALL_CAPABILITIES:
            self.session_overrides[cap] = None

    def snapshot(self) -> dict[str, bool]:
        return {cap: self.is_allowed(cap) for cap in ALL_CAPABILITIES}


def parse_capability(value: str) -> Capability:
    normalized = value.strip().lower()
    if normalized not in ALL_CAPABILITIES:
        raise ValueError(f"Unknown capability '{value}'. Expected one of: {', '.join(ALL_CAPABILITIES)}")
    return normalized  # type: ignore[return-value]
