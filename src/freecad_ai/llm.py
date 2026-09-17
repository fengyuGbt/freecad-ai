"""Minimal OpenAI-compatible chat client with tool-calling support.

Zero third-party dependencies (stdlib ``urllib`` only), so it works inside
FreeCAD's bundled Python without installing anything.

Any endpoint that speaks the OpenAI Chat Completions protocol works:
OpenAI, DeepSeek, Moonshot, Qwen, Groq, or a local server (vLLM / Ollama
with the OpenAI-compatible mode).

Configuration via environment variables:
    OPENAI_API_KEY     required
    OPENAI_BASE_URL    default https://api.openai.com/v1
    OPENAI_MODEL       default gpt-4o-mini
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


class LLMError(Exception):
    """Raised for configuration errors and failed HTTP calls."""


class ChatClient:
    """Tiny Chat Completions client; only implements what the agent needs."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout: int = 60,
    ) -> None:
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY") or ""
        self.base_url = (
            base_url or os.environ.get("OPENAI_BASE_URL") or "https://api.openai.com/v1"
        ).rstrip("/")
        self.model = model or os.environ.get("OPENAI_MODEL") or "gpt-4o-mini"
        self.timeout = timeout

    # ------------------------------------------------------------------
    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        """POST /chat/completions and return the parsed JSON response."""
        if not self.api_key:
            raise LLMError(
                "OPENAI_API_KEY is not set — configure it (or pass api_key=...) "
                "before running the agent loop."
            )

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if tools:
            payload["tools"] = [{"type": "function", "function": t} for t in tools]

        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise LLMError(f"HTTP {exc.code} from {self.base_url}: {body[:500]}") from exc
        except urllib.error.URLError as exc:
            raise LLMError(f"Network error talking to {self.base_url}: {exc.reason}") from exc
        except Exception as exc:  # timeout, JSON decode, ...
            raise LLMError(f"LLM call failed: {exc}") from exc
