from __future__ import annotations

import json
import re
from typing import Any

import httpx

from .types import Message, ToolCall


class OpenAIAdapter:
    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1") -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.client = httpx.Client(timeout=60)

    def complete(self, messages: list[Message], model: str, stream: bool = False) -> str:
        payload = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": stream,
        }
        data = self._post_chat(payload)
        return data["choices"][0]["message"]["content"]

    def complete_with_tools(
        self,
        messages: list[Message],
        tools_schema: list[dict[str, Any]],
        model: str,
    ) -> dict[str, Any]:
        instruction = (
            "You may either reply with normal text or emit exactly one tool call as JSON. "
            "Tool call JSON format: {\"tool\":\"name\",\"args\":{...}}. "
            "When task is finished, reply with: DONE: <summary>."
        )
        tool_schema_text = json.dumps(tools_schema, indent=2)
        prompt_messages = [
            *messages,
            Message(
                role="system",
                content=f"{instruction}\n\nAllowed tools schema:\n{tool_schema_text}",
            ),
        ]

        text = self.complete(prompt_messages, model=model, stream=False)

        if text.strip().startswith("DONE:"):
            return {"type": "text", "text": text}

        tool_call = self._extract_tool_call(text)
        if tool_call is None:
            return {"type": "text", "text": text}
        return {"type": "tool_call", "tool_call": tool_call}

    def health_check(self) -> tuple[bool, str]:
        try:
            res = self.client.get(
                f"{self.base_url}/models",
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            if res.status_code == 200:
                return True, "API reachable"
            return False, f"API error: {res.status_code} {res.text[:200]}"
        except Exception as exc:
            return False, f"Connection failed: {exc}"

    def _post_chat(self, payload: dict[str, Any]) -> dict[str, Any]:
        res = self.client.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        res.raise_for_status()
        return res.json()

    def _extract_tool_call(self, text: str) -> ToolCall | None:
        candidate = text.strip()
        if candidate.startswith("{"):
            try:
                data = json.loads(candidate)
                if "tool" in data and "args" in data:
                    return ToolCall(tool=str(data["tool"]), args=dict(data["args"]))
            except json.JSONDecodeError:
                pass

        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            return None
        try:
            data = json.loads(match.group(0))
            if "tool" in data and "args" in data:
                return ToolCall(tool=str(data["tool"]), args=dict(data["args"]))
        except json.JSONDecodeError:
            return None
        return None
