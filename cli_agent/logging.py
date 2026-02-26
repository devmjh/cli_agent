from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .config import get_log_dir


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class RunLogger:
    def __init__(self) -> None:
        self.run_id = str(uuid4())
        self.log_dir = get_log_dir()
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.path = Path(self.log_dir) / f"run-{self.run_id}.jsonl"

    def event(self, event_type: str, payload: dict) -> None:
        record = {
            "ts": _utc_now(),
            "run_id": self.run_id,
            "event": event_type,
            "payload": payload,
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
