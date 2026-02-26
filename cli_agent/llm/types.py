from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

Role = Literal["system", "user", "assistant", "tool"]


@dataclass
class Message:
    role: Role
    content: str


@dataclass
class ToolCall:
    tool: str
    args: dict[str, Any]
