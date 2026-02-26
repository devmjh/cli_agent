from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from rich.console import Console
from rich.prompt import Prompt

from .agent.loop import AgentLoop
from .config import AppConfig
from .llm.openai_adapter import OpenAIAdapter
from .llm.types import Message
from .permissions import PermissionState, parse_capability
from .tools.git_tools import git_diff
from .workspace import Workspace, WorkspaceError


@dataclass
class ReplSession:
    model: str
    workspace_root: str
    permissions: PermissionState
    messages: list[Message] = field(default_factory=list)


def start_chat(config: AppConfig, llm: OpenAIAdapter) -> None:
    console = Console()
    permissions = PermissionState(defaults=config.permissions.copy())
    session = ReplSession(
        model=config.model,
        workspace_root=config.workspace_root,
        permissions=permissions,
    )

    console.print("[bold cyan]CLI Agent chat[/bold cyan]. Type /help for commands.")

    while True:
        user_input = Prompt.ask("[green]you[/green]").strip()
        if not user_input:
            continue

        if user_input.startswith("/"):
            should_exit = _handle_slash(user_input, session, config, llm, console)
            if should_exit:
                return
            continue

        session.messages.append(Message(role="user", content=user_input))
        try:
            text = llm.complete(session.messages, model=session.model)
        except Exception as exc:
            console.print(f"[red]LLM error:[/red] {exc}")
            continue

        session.messages.append(Message(role="assistant", content=text))
        console.print(f"[cyan]assistant:[/cyan] {text}")


def _handle_slash(
    raw: str,
    session: ReplSession,
    config: AppConfig,
    llm: OpenAIAdapter,
    console: Console,
) -> bool:
    parts = raw.split(maxsplit=1)
    command = parts[0].lower()
    arg = parts[1].strip() if len(parts) > 1 else ""

    if command == "/help":
        console.print(
            "Commands: /help /exit /model <m> /status /allow <cap> /deny <cap> "
            "/workspace <path> /run [goal] /diff /reset"
        )
        return False

    if command == "/exit":
        return True

    if command == "/model":
        if not arg:
            console.print(f"Current model: {session.model}")
            return False
        session.model = arg
        config.model = arg
        console.print(f"Model set to {arg}")
        return False

    if command == "/status":
        perms = session.permissions.snapshot()
        console.print(
            f"model={session.model} workspace={session.workspace_root} "
            f"perms={perms}"
        )
        return False

    if command == "/allow":
        try:
            cap = parse_capability(arg)
            session.permissions.allow(cap)
            console.print(f"Allowed {cap} for this session")
        except Exception as exc:
            console.print(f"[red]{exc}[/red]")
        return False

    if command == "/deny":
        try:
            cap = parse_capability(arg)
            session.permissions.deny(cap)
            console.print(f"Denied {cap} for this session")
        except Exception as exc:
            console.print(f"[red]{exc}[/red]")
        return False

    if command == "/workspace":
        if not arg:
            console.print(f"Current workspace: {session.workspace_root}")
            return False
        try:
            Workspace(arg)
            session.workspace_root = arg
            config.workspace_root = arg
            console.print(f"Workspace set to {arg}")
        except WorkspaceError as exc:
            console.print(f"[red]{exc}[/red]")
        return False

    if command == "/run":
        goal = arg or Prompt.ask("Goal")
        try:
            workspace = Workspace(session.workspace_root)
        except WorkspaceError as exc:
            console.print(f"[red]{exc}[/red]")
            return False
        loop = AgentLoop(
            llm=llm,
            permissions=session.permissions,
            workspace=workspace,
            model=session.model,
            auto_approve=False,
            console=console,
        )
        result = loop.run(goal, history=session.messages)
        console.print(result.summary)
        return False

    if command == "/diff":
        out = git_diff(Path(session.workspace_root))
        if out["ok"]:
            console.print(out["stdout"] or "(no diff)")
        else:
            console.print(f"[red]{out['stderr'] or out['stdout']}[/red]")
        return False

    if command == "/reset":
        session.messages.clear()
        session.permissions.reset_overrides()
        console.print("Conversation and session permission overrides reset")
        return False

    console.print(f"Unknown command: {command}")
    return False
