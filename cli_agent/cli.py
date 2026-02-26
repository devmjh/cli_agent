from __future__ import annotations

import os
from pathlib import Path

import typer
from dotenv import load_dotenv
from rich.console import Console

from .agent.loop import AgentLoop
from .config import AppConfig, load_config, save_config
from .llm.openai_adapter import OpenAIAdapter
from .permissions import PermissionState, parse_capability
from .repl import start_chat
from .workspace import Workspace, WorkspaceError


app = typer.Typer(help="CLI Agent")
config_app = typer.Typer(help="Manage persistent settings")
app.add_typer(config_app, name="config")


def _load_env() -> None:
    load_dotenv(Path.home() / ".env", override=False)
    load_dotenv(override=False)


def _effective_model(cfg: AppConfig) -> str:
    return os.getenv("OPENAI_MODEL", cfg.model)


def _build_adapter() -> OpenAIAdapter:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is missing. Set env var or ~/.env")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    return OpenAIAdapter(api_key=api_key, base_url=base_url)


@app.command()
def chat() -> None:
    """Interactive REPL."""
    _load_env()
    cfg = load_config()
    cfg.model = _effective_model(cfg)
    llm = _build_adapter()
    start_chat(cfg, llm)
    save_config(cfg)


@app.command()
def run(
    goal: str,
    yes: bool = typer.Option(False, "--yes", help="Auto-approve permitted tool calls"),
    workspace: str | None = typer.Option(None, "--workspace", help="Workspace root path"),
) -> None:
    """Non-interactive single task run."""
    _load_env()
    cfg = load_config()
    cfg.model = _effective_model(cfg)
    workspace_root = workspace or cfg.workspace_root
    if workspace is not None:
        cfg.workspace_root = workspace

    console = Console()
    llm = _build_adapter()
    permissions = PermissionState(defaults=cfg.permissions.copy())
    try:
        ws = Workspace(workspace_root)
    except WorkspaceError as exc:
        raise typer.Exit(str(exc))

    loop = AgentLoop(
        llm=llm,
        permissions=permissions,
        workspace=ws,
        model=cfg.model,
        auto_approve=yes,
        console=console,
    )
    result = loop.run(goal)
    console.print(result.summary)
    save_config(cfg)


@app.command()
def doctor(workspace: str | None = typer.Option(None, "--workspace")) -> None:
    """Validate environment, config, and connectivity."""
    _load_env()
    cfg = load_config()
    cfg.model = _effective_model(cfg)
    workspace_root = workspace or cfg.workspace_root
    console = Console()

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if api_key:
        console.print("[green]✓[/green] OPENAI_API_KEY present")
    else:
        console.print("[red]✗ OPENAI_API_KEY missing[/red]")

    try:
        ws = Workspace(workspace_root)
        console.print(f"[green]✓[/green] Workspace exists: {ws.root}")
    except WorkspaceError as exc:
        console.print(f"[red]✗ Workspace invalid:[/red] {exc}")
        ws = None

    if ws and cfg.permissions.get("write", False):
        can_write = os.access(ws.root, os.W_OK)
        if can_write:
            console.print("[green]✓[/green] Workspace writable (write permission enabled)")
        else:
            console.print("[red]✗ Workspace not writable (write permission enabled)[/red]")

    if api_key:
        try:
            llm = _build_adapter()
            ok, msg = llm.health_check()
            if ok:
                console.print(f"[green]✓[/green] API connectivity: {msg}")
            else:
                console.print(f"[red]✗ API connectivity:[/red] {msg}")
        except Exception as exc:
            console.print(f"[red]✗ API check failed:[/red] {exc}")


@config_app.command("show")
def config_show() -> None:
    """Show persisted config."""
    cfg = load_config()
    console = Console()
    console.print(
        {
            "model": cfg.model,
            "workspace_root": cfg.workspace_root,
            "permissions": cfg.permissions,
            "logging": {"enabled": cfg.logging.enabled},
        }
    )


@config_app.command("set")
def config_set(key: str, value: str) -> None:
    """Set config value. Example: cli-agent config set model gpt-4o"""
    cfg = load_config()
    if key == "model":
        cfg.model = value
    elif key == "workspace_root":
        cfg.workspace_root = value
    elif key.startswith("permissions."):
        cap = parse_capability(key.split(".", 1)[1])
        cfg.permissions[cap] = value.lower() in {"1", "true", "yes", "on"}
    elif key == "logging.enabled":
        cfg.logging.enabled = value.lower() in {"1", "true", "yes", "on"}
    else:
        raise typer.BadParameter("Unsupported key")
    save_config(cfg)
    Console().print(f"Updated {key}={value}")


if __name__ == "__main__":
    app()
