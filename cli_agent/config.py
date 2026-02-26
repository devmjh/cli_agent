from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from platformdirs import PlatformDirs


APP_NAME = "cli-agent"
APP_AUTHOR = "cli-agent"


@dataclass
class LoggingConfig:
    enabled: bool = True


@dataclass
class AppConfig:
    model: str = "gpt-4o"
    workspace_root: str = "."
    permissions: dict[str, bool] = field(
        default_factory=lambda: {
            "read": False,
            "write": False,
            "shell": False,
            "net": False,
        }
    )
    logging: LoggingConfig = field(default_factory=LoggingConfig)


def get_dirs() -> PlatformDirs:
    return PlatformDirs(APP_NAME, APP_AUTHOR)


def get_config_path() -> Path:
    dirs = get_dirs()
    return Path(dirs.user_config_dir) / "config.toml"


def get_log_dir() -> Path:
    dirs = get_dirs()
    return Path(dirs.user_log_dir)


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def load_config() -> AppConfig:
    path = get_config_path()
    if not path.exists():
        return AppConfig()
    data = tomllib.loads(path.read_text(encoding="utf-8"))

    cfg = AppConfig()
    cfg.model = str(data.get("model", cfg.model))
    cfg.workspace_root = str(data.get("workspace_root", cfg.workspace_root))

    perms = data.get("permissions", {})
    for key in cfg.permissions:
        if key in perms:
            cfg.permissions[key] = bool(perms[key])

    logging_data = data.get("logging", {})
    cfg.logging.enabled = bool(logging_data.get("enabled", cfg.logging.enabled))
    return cfg


def _to_toml(cfg: AppConfig) -> str:
    def b(value: bool) -> str:
        return "true" if value else "false"

    return (
        f'model = "{cfg.model}"\n'
        f'workspace_root = "{cfg.workspace_root}"\n\n'
        "[permissions]\n"
        f'read = {b(cfg.permissions["read"])}\n'
        f'write = {b(cfg.permissions["write"])}\n'
        f'shell = {b(cfg.permissions["shell"])}\n'
        f'net = {b(cfg.permissions["net"])}\n\n'
        "[logging]\n"
        f"enabled = {b(cfg.logging.enabled)}\n"
    )


def save_config(cfg: AppConfig) -> None:
    path = get_config_path()
    ensure_parent(path)
    path.write_text(_to_toml(cfg), encoding="utf-8")
