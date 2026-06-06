"""
Provider-neutral LLM client.

The Agent speaks one internal "block" dialect (Anthropic-style):
  - request messages: [{"role", "content"}] where content is either a string
    or a list of blocks:
        assistant -> [{"type":"text","text"}, {"type":"tool_use","id","name","input"}]
        user      -> [{"type":"tool_result","tool_use_id","content"(json str)}]
  - tool defs:     [{"name","description","input_schema"}]
  - response:      [{"type":"text","text"} | {"type":"tool_use","id","name","input"}]

This module keeps that dialect as the lingua franca and adapts it to whichever
provider is configured. Two backends ship:

  * GroqClient      — OpenAI-compatible Chat Completions (Groq, Gemini-OpenAI,
                      OpenRouter, local llama.cpp, ...). FREE-tier friendly.
                      This is the default and incurs no paid-API cost on Groq.
  * AnthropicClient — thin wrapper over the Anthropic SDK (optional, paid).

Use `make_client(...)` — it picks the backend from config and never forces the
`anthropic` package to be importable unless that backend is actually selected.
"""

from __future__ import annotations

import json
import logging
from typing import Optional, Protocol

import httpx

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Interface
# ─────────────────────────────────────────────────────────────────────────────

class LLMClient(Protocol):
    """Minimal contract the Agent depends on."""

    async def chat_raw(
        self,
        messages: list[dict],
        model: str,
        system: Optional[str] = None,
        max_tokens: int = 2048,
        tools: Optional[list[dict]] = None,
        temperature: float = 0.7,
    ) -> list[dict]: ...

    async def chat(
        self,
        messages: list[dict],
        model: str,
        system: Optional[str] = None,
        max_tokens: int = 2048,
        tools: Optional[list[dict]] = None,
        temperature: float = 0.7,
    ) -> str: ...

    async def health_check(self) -> bool: ...


# ─────────────────────────────────────────────────────────────────────────────
# Format bridge: internal (Anthropic-style) <-> OpenAI chat-completions
# ─────────────────────────────────────────────────────────────────────────────

def _tools_to_openai(tools: Optional[list[dict]]) -> Optional[list[dict]]:
    if not tools:
        return None
    out = []
    for t in tools:
        out.append({
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t.get("description", ""),
                "parameters": t.get("input_schema", {"type": "object", "properties": {}}),
            },
        })
    return out


def _messages_to_openai(messages: list[dict], system: Optional[str]) -> list[dict]:
    """Translate the Agent's internal message list into OpenAI format."""
    out: list[dict] = []
    if system:
        out.append({"role": "system", "content": system})

    for msg in messages:
        role = msg["role"]
        content = msg["content"]

        # Plain string content (normal user / assistant text turns)
        if isinstance(content, str):
            out.append({"role": role, "content": content})
            continue

        # Block-list content
        if role == "assistant":
            text_parts: list[str] = []
            tool_calls: list[dict] = []
            for block in content:
                btype = block.get("type")
                if btype == "text":
                    text_parts.append(block.get("text", ""))
                elif btype == "tool_use":
                    tool_calls.append({
                        "id": block["id"],
                        "type": "function",
                        "function": {
                            "name": block["name"],
                            "arguments": json.dumps(block.get("input", {})),
                        },
                    })
            assistant_msg: dict = {"role": "assistant"}
            assistant_msg["content"] = "\n".join(p for p in text_parts if p) or None
            if tool_calls:
                assistant_msg["tool_calls"] = tool_calls
            out.append(assistant_msg)

        else:  # user turn carrying tool_result blocks
            for block in content:
                if block.get("type") == "tool_result":
                    tool_content = block.get("content", "")
                    if not isinstance(tool_content, str):
                        tool_content = json.dumps(tool_content)
                    out.append({
                        "role": "tool",
                        "tool_call_id": block["tool_use_id"],
                        "content": tool_content,
                    })
                elif block.get("type") == "text":
                    out.append({"role": "user", "content": block.get("text", "")})

    return out


def _openai_response_to_blocks(message: dict) -> list[dict]:
    """Translate one OpenAI assistant message back into internal blocks."""
    blocks: list[dict] = []
    text = message.get("content")
    if text:
        blocks.append({"type": "text", "text": text})
    for tc in message.get("tool_calls") or []:
        fn = tc.get("function", {})
        raw_args = fn.get("arguments") or "{}"
        try:
            parsed = json.loads(raw_args)
        except (json.JSONDecodeError, TypeError):
            parsed = {}
        if not isinstance(parsed, dict):  # e.g. arguments == "null" or a list
            parsed = {}
        blocks.append({
            "type": "tool_use",
            "id": tc.get("id", ""),
            "name": fn.get("name", ""),
            "input": parsed,
        })
    return blocks


# ─────────────────────────────────────────────────────────────────────────────
# Groq / OpenAI-compatible backend (default, free-tier friendly)
# ─────────────────────────────────────────────────────────────────────────────

class GroqClient:
    """
    OpenAI-compatible Chat Completions client over httpx.

    Defaults to Groq's free endpoint. Point `base_url` elsewhere to use any
    other OpenAI-compatible provider (Gemini-OpenAI, OpenRouter, local server).
    No vendor SDK required — just httpx (already a dependency).
    """

    DEFAULT_BASE_URL = "https://api.groq.com/openai/v1"

    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        timeout: int = 30,
    ):
        if not api_key:
            raise ValueError(
                "GroqClient needs an API key. Set GROQ_API_KEY (Groq's free tier) "
                "or LLM_API_KEY for another OpenAI-compatible provider."
            )
        self.api_key = api_key
        self.base_url = (base_url or self.DEFAULT_BASE_URL).rstrip("/")
        self.timeout = timeout

    async def _post(self, payload: dict) -> dict:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=self.timeout) as http:
            resp = await http.post(url, headers=headers, json=payload)
        if resp.status_code >= 400:
            logger.error("LLM HTTP %s: %s", resp.status_code, resp.text[:500])
            resp.raise_for_status()
        return resp.json()

    async def chat_raw(
        self,
        messages: list[dict],
        model: str,
        system: Optional[str] = None,
        max_tokens: int = 2048,
        tools: Optional[list[dict]] = None,
        temperature: float = 0.7,
    ) -> list[dict]:
        payload: dict = {
            "model": model,
            "messages": _messages_to_openai(messages, system),
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        oai_tools = _tools_to_openai(tools)
        if oai_tools:
            payload["tools"] = oai_tools
            payload["tool_choice"] = "auto"

        try:
            data = await self._post(payload)
            message = data["choices"][0]["message"]
            return _openai_response_to_blocks(message)
        except httpx.HTTPStatusError as e:
            # Some open models (Llama on Groq) occasionally emit a malformed
            # function call -> HTTP 400 "tool_use_failed". Salvage the turn by
            # retrying once WITHOUT tools so the model answers in plain text.
            if self._is_tool_use_failure(e) and oai_tools:
                logger.warning("tool_use_failed — retrying without tools")
                payload.pop("tools", None)
                payload.pop("tool_choice", None)
                data = await self._post(payload)
                message = data["choices"][0]["message"]
                return _openai_response_to_blocks(message)
            logger.error(f"GroqClient.chat_raw error: {e}")
            raise
        except Exception as e:
            logger.error(f"GroqClient.chat_raw error: {e}")
            raise

    @staticmethod
    def _is_tool_use_failure(e: httpx.HTTPStatusError) -> bool:
        if e.response is None or e.response.status_code != 400:
            return False
        try:
            body = e.response.json()
        except Exception:
            return "tool_use_failed" in (e.response.text or "")
        err = body.get("error", {}) if isinstance(body, dict) else {}
        return err.get("code") == "tool_use_failed" or "tool_use_failed" in str(err)

    async def chat(
        self,
        messages: list[dict],
        model: str,
        system: Optional[str] = None,
        max_tokens: int = 2048,
        tools: Optional[list[dict]] = None,
        temperature: float = 0.7,
    ) -> str:
        blocks = await self.chat_raw(
            messages=messages, model=model, system=system,
            max_tokens=max_tokens, tools=tools, temperature=temperature,
        )
        return "".join(b["text"] for b in blocks if b.get("type") == "text")

    async def health_check(self) -> bool:
        data = await self._post({
            "model": self._probe_model,
            "messages": [{"role": "user", "content": "ping"}],
            "max_tokens": 5,
        })
        return bool(data.get("choices"))

    # Probe model is set by make_client so health_check uses a valid id.
    _probe_model = "llama-3.1-8b-instant"


# ─────────────────────────────────────────────────────────────────────────────
# Anthropic backend (optional, paid) — imported lazily
# ─────────────────────────────────────────────────────────────────────────────

class AnthropicClient:
    """Thin wrapper over the Anthropic SDK. Only used if provider='anthropic'."""

    def __init__(self, api_key: str, timeout: int = 30):
        from anthropic import AsyncAnthropic  # lazy: don't require the dep otherwise
        if not api_key:
            raise ValueError("AnthropicClient needs ANTHROPIC_API_KEY.")
        self._async = AsyncAnthropic(api_key=api_key)
        self.timeout = timeout

    async def chat_raw(
        self,
        messages: list[dict],
        model: str,
        system: Optional[str] = None,
        max_tokens: int = 2048,
        tools: Optional[list[dict]] = None,
        temperature: float = 0.7,
    ) -> list[dict]:
        kwargs = dict(
            model=model, max_tokens=max_tokens, system=system,
            messages=messages, temperature=temperature,
        )
        if tools:
            kwargs["tools"] = tools
        response = await self._async.messages.create(**kwargs)
        blocks = []
        for block in response.content:
            if hasattr(block, "text"):
                blocks.append({"type": "text", "text": block.text})
            elif hasattr(block, "name"):
                blocks.append({
                    "type": "tool_use",
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                })
        return blocks

    async def chat(self, **kw) -> str:
        blocks = await self.chat_raw(**kw)
        return "".join(b["text"] for b in blocks if b.get("type") == "text")

    async def health_check(self) -> bool:
        await self._async.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=10,
            messages=[{"role": "user", "content": "ping"}],
        )
        return True


# ─────────────────────────────────────────────────────────────────────────────
# Factory
# ─────────────────────────────────────────────────────────────────────────────

def make_client(
    provider: str,
    *,
    groq_api_key: Optional[str] = None,
    anthropic_api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    probe_model: Optional[str] = None,
    timeout: int = 30,
) -> LLMClient:
    """
    Build the configured LLM client.

    provider:
      "groq" | "openai" | "gemini" | "openrouter" | "local"  -> GroqClient
      "anthropic"                                             -> AnthropicClient
    """
    provider = (provider or "groq").lower()

    if provider == "anthropic":
        return AnthropicClient(api_key=anthropic_api_key or "", timeout=timeout)

    # Everything else is treated as OpenAI-compatible.
    client = GroqClient(
        api_key=groq_api_key or "",
        base_url=base_url,
        timeout=timeout,
    )
    if probe_model:
        client._probe_model = probe_model
    return client
