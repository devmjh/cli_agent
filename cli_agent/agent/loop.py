from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console
from rich.prompt import Confirm

from ..llm.openai_adapter import OpenAIAdapter
from ..llm.types import Message
from ..logging import RunLogger
from ..permissions import PermissionState
from ..tools.fs_tools import apply_patch, list_dir, read_file, write_file
from ..tools.shell_tools import run_shell
from ..workspace import Workspace
from .prompts import SYSTEM_PROMPT


@dataclass
class AgentRunResult:
    ok: bool
    summary: str
    iterations: int


class AgentLoop:
    def __init__(
        self,
        llm: OpenAIAdapter,
        permissions: PermissionState,
        workspace: Workspace,
        model: str,
        auto_approve: bool = False,
        max_iterations: int = 20,
        console: Console | None = None,
    ) -> None:
        self.llm = llm
        self.permissions = permissions
        self.workspace = workspace
        self.model = model
        self.auto_approve = auto_approve
        self.max_iterations = max_iterations
        self.console = console or Console()
        self.logger = RunLogger()

    def run(self, goal: str, history: list[Message] | None = None) -> AgentRunResult:
        messages = [Message(role="system", content=SYSTEM_PROMPT)]
        if history:
            messages.extend(history)
        messages.append(Message(role="user", content=goal))

        for i in range(1, self.max_iterations + 1):
            self.logger.event("iteration", {"iteration": i})
            response = self.llm.complete_with_tools(messages, self._tools_schema(), self.model)

            if response["type"] == "text":
                text = response["text"]
                self.logger.event("assistant_text", {"text": text})
                messages.append(Message(role="assistant", content=text))
                if text.strip().startswith("DONE:"):
                    return AgentRunResult(ok=True, summary=text, iterations=i)
                continue

            tool_call = response["tool_call"]
            tool_name = tool_call.tool
            args = tool_call.args

            allowed, denial = self._tool_allowed(tool_name)
            if not allowed:
                result = {"ok": False, "error": denial}
                self.logger.event("tool_denied", {"tool": tool_name, "reason": denial})
            elif not self.auto_approve and not Confirm.ask(
                f"Allow tool call: {tool_name}({json.dumps(args)})?", default=False
            ):
                result = {"ok": False, "error": "User denied tool call"}
                self.logger.event("tool_denied", {"tool": tool_name, "reason": "user_denied"})
            else:
                result = self._execute_tool(tool_name, args)
                self.logger.event("tool_call", {"tool": tool_name, "args": args, "result": result})

            messages.append(
                Message(
                    role="tool",
                    content=json.dumps({"tool_result": {"tool": tool_name, **result}}, ensure_ascii=False),
                )
            )

        return AgentRunResult(ok=False, summary="Max iterations reached without DONE", iterations=self.max_iterations)

    def _tools_schema(self) -> list[dict]:
        return [
            {"name": "list_dir", "args": {"path": "string"}},
            {"name": "read_file", "args": {"path": "string"}},
            {"name": "write_file", "args": {"path": "string", "content": "string"}},
            {"name": "apply_patch", "args": {"unified_diff": "string"}},
            {"name": "run_shell", "args": {"cmd": "string", "cwd": "string"}},
        ]

    def _tool_allowed(self, tool_name: str) -> tuple[bool, str]:
        capability_map = {
            "list_dir": "read",
            "read_file": "read",
            "write_file": "write",
            "apply_patch": "write",
            "run_shell": "shell",
        }
        cap = capability_map.get(tool_name)
        if cap is None:
            return False, f"Unknown tool: {tool_name}"
        if not self.permissions.is_allowed(cap):
            return False, f"Permission denied for capability: {cap}"
        return True, ""

    def _execute_tool(self, tool_name: str, args: dict) -> dict:
        try:
            if tool_name == "list_dir":
                return {"ok": True, **list_dir(self.workspace, path=str(args.get("path", ".")))}
            if tool_name == "read_file":
                return read_file(self.workspace, path=str(args["path"]))
            if tool_name == "write_file":
                return write_file(self.workspace, path=str(args["path"]), content=str(args.get("content", "")))
            if tool_name == "apply_patch":
                return apply_patch(self.workspace, unified_diff=str(args.get("unified_diff", "")))
            if tool_name == "run_shell":
                tool_cwd = str(args.get("cwd", "."))
                safe_cwd = self.workspace.resolve_safe(Path(tool_cwd))
                return run_shell(str(args.get("cmd", "")), cwd=safe_cwd)
            return {"ok": False, "error": f"Unknown tool: {tool_name}"}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
