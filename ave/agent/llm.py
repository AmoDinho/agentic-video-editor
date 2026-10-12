from __future__ import annotations

import json
import uuid
from typing import Any, Literal

import httpx

from ave.config import LLMConfig
from ave.secrets import get_api_key

Provider = Literal["ollama", "anthropic", "openai", "openai_compatible"]


class ToolCall:
    def __init__(self, id: str, name: str, arguments: dict[str, Any]):
        self.id = id
        self.name = name
        self.arguments = arguments


class LLMMessage:
    def __init__(
        self,
        role: str,
        content: str | None = None,
        tool_calls: list[ToolCall] | None = None,
        tool_call_id: str | None = None,
        name: str | None = None,
    ):
        self.role = role
        self.content = content
        self.tool_calls = tool_calls or []
        self.tool_call_id = tool_call_id
        self.name = name


class LLMClient:
    def __init__(self, cfg: LLMConfig):
        self.cfg = cfg
        self.tokens_used = 0

    def chat(
        self,
        messages: list[LLMMessage],
        tools: list[dict[str, Any]],
        *,
        temperature: float = 0.2,
    ) -> LLMMessage:
        if self.cfg.provider == "ollama":
            return self._ollama(messages, tools, temperature)
        if self.cfg.provider == "anthropic":
            return self._anthropic(messages, tools, temperature)
        return self._openai(messages, tools, temperature)

    def remaining_tokens(self) -> int:
        return max(0, self.cfg.max_tokens_per_run - self.tokens_used)

    def _ollama(self, messages, tools, temperature) -> LLMMessage:
        payload = {
            "model": self.cfg.model,
            "messages": [_to_ollama(m) for m in messages],
            "stream": False,
            "keep_alive": 0,
            "options": {"temperature": temperature},
        }
        if tools:
            payload["tools"] = tools
        r = httpx.post(
            f"{self.cfg.base_url.rstrip('/')}/api/chat",
            json=payload,
            timeout=180,
        )
        r.raise_for_status()
        data = r.json()
        self.tokens_used += int(
            (data.get("eval_count") or 0) + (data.get("prompt_eval_count") or 0)
        )
        msg = data.get("message") or {}
        calls = []
        for tc in msg.get("tool_calls") or []:
            fn = tc.get("function") or tc
            args = fn.get("arguments") or {}
            if isinstance(args, str):
                args = json.loads(args or "{}")
            calls.append(
                ToolCall(
                    id=str(uuid.uuid4()),
                    name=fn.get("name") or tc.get("name"),
                    arguments=args,
                )
            )
        return LLMMessage(role="assistant", content=msg.get("content") or "", tool_calls=calls)

    def _openai(self, messages, tools, temperature) -> LLMMessage:
        key = get_api_key(self.cfg.provider, self.cfg.api_key_env)
        if not key:
            raise RuntimeError(f"missing API key for {self.cfg.provider}")
        base = self.cfg.base_url.rstrip("/")
        if self.cfg.provider == "openai":
            base = "https://api.openai.com/v1"
        url = f"{base}/chat/completions"
        oai_tools = [
            {"type": "function", "function": t["function"]} if "function" in t else t for t in tools
        ]
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        r = httpx.post(
            url,
            headers=headers,
            json={
                "model": self.cfg.model,
                "messages": [_to_openai(m) for m in messages],
                "tools": oai_tools or None,
                "temperature": temperature,
            },
            timeout=180,
        )
        r.raise_for_status()
        data = r.json()
        usage = data.get("usage") or {}
        self.tokens_used += int(usage.get("total_tokens") or 0)
        choice = (data.get("choices") or [{}])[0].get("message") or {}
        calls = []
        for tc in choice.get("tool_calls") or []:
            fn = tc.get("function") or {}
            args = fn.get("arguments") or "{}"
            if isinstance(args, str):
                args = json.loads(args or "{}")
            calls.append(ToolCall(id=tc.get("id") or str(uuid.uuid4()), name=fn.get("name"), arguments=args))
        return LLMMessage(role="assistant", content=choice.get("content") or "", tool_calls=calls)

    def _anthropic(self, messages, tools, temperature) -> LLMMessage:
        key = get_api_key("anthropic", self.cfg.api_key_env)
        if not key:
            raise RuntimeError("missing API key for anthropic")
        sys_parts = [m.content for m in messages if m.role == "system" and m.content]
        body_msgs = [m for m in messages if m.role != "system"]
        anth_tools = []
        for t in tools:
            fn = t.get("function") or t
            anth_tools.append(
                {
                    "name": fn["name"],
                    "description": fn.get("description") or "",
                    "input_schema": fn.get("parameters") or {"type": "object", "properties": {}},
                }
            )
        r = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": self.cfg.model,
                "max_tokens": 4096,
                "temperature": temperature,
                "system": "\n".join(sys_parts),
                "tools": anth_tools,
                "messages": [_to_anthropic(m) for m in body_msgs],
            },
            timeout=180,
        )
        r.raise_for_status()
        data = r.json()
        usage = data.get("usage") or {}
        self.tokens_used += int((usage.get("input_tokens") or 0) + (usage.get("output_tokens") or 0))
        text = ""
        calls = []
        for block in data.get("content") or []:
            if block.get("type") == "text":
                text += block.get("text") or ""
            elif block.get("type") == "tool_use":
                calls.append(
                    ToolCall(
                        id=block.get("id") or str(uuid.uuid4()),
                        name=block.get("name"),
                        arguments=block.get("input") or {},
                    )
                )
        return LLMMessage(role="assistant", content=text, tool_calls=calls)


def _to_ollama(m: LLMMessage) -> dict[str, Any]:
    msg: dict[str, Any] = {"role": m.role, "content": m.content or ""}
    if m.role == "tool":
        msg["role"] = "tool"
        msg["content"] = m.content or ""
    if m.tool_calls:
        msg["tool_calls"] = [
            {"function": {"name": tc.name, "arguments": tc.arguments}} for tc in m.tool_calls
        ]
    return msg


def _to_openai(m: LLMMessage) -> dict[str, Any]:
    msg: dict[str, Any] = {"role": m.role, "content": m.content or ""}
    if m.role == "tool":
        msg["tool_call_id"] = m.tool_call_id
        msg["name"] = m.name
    if m.tool_calls:
        msg["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {"name": tc.name, "arguments": json.dumps(tc.arguments)},
            }
            for tc in m.tool_calls
        ]
    return msg


def _to_anthropic(m: LLMMessage) -> dict[str, Any]:
    if m.role == "tool":
        return {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": m.tool_call_id,
                    "content": m.content or "",
                }
            ],
        }
    if m.tool_calls:
        content: list[dict[str, Any]] = []
        if m.content:
            content.append({"type": "text", "text": m.content})
        for tc in m.tool_calls:
            content.append({"type": "tool_use", "id": tc.id, "name": tc.name, "input": tc.arguments})
        return {"role": "assistant", "content": content}
    return {"role": m.role, "content": m.content or ""}
