#!/usr/bin/env python3
"""OpenRouter client + the five 2026 frontier models used for v6 benchmarking.

Reads OPENROUTER_API_KEY from the environment. Never prints it.
Standard library only, matching the rest of the project.

Usage from other scripts:

    from models import chat, MODELS

    text = chat("anthropic/claude-opus-5", "写一段关于时间管理的短文")
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Verified callable on OpenRouter 2026-08-24. Keep this list in sync with
# projects/v6-refactor/GOAL.md H4 — it is the frozen benchmark panel.
MODELS = [
    "anthropic/claude-opus-5",
    "openai/gpt-5.6-sol",
    "deepseek/deepseek-v4-pro-0813",
    "z-ai/glm-5.3",
    "moonshotai/kimi-k3",
]

# Short labels for filenames and tables.
SHORT = {
    "anthropic/claude-opus-5": "opus5",
    "openai/gpt-5.6-sol": "gpt56",
    "deepseek/deepseek-v4-pro-0813": "dsv4",
    "z-ai/glm-5.3": "glm53",
    "moonshotai/kimi-k3": "kimi3",
}


class OpenRouterError(RuntimeError):
    pass


def _api_key() -> str:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise OpenRouterError(
            "OPENROUTER_API_KEY not in environment. "
            "Run via: secret exec OPENROUTER_API_KEY -- python3 <script>"
        )
    return key


def chat(model: str, prompt: str, *, system: str | None = None,
         max_tokens: int = 8000, temperature: float | None = None,
         retries: int = 3, timeout: int = 300) -> str:
    """One-shot completion. Returns assistant text, raises on hard failure.

    Reasoning models on OpenRouter spend part of max_tokens on hidden reasoning,
    so max_tokens defaults high enough that the visible answer is not truncated.
    """
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {"model": model, "messages": messages, "max_tokens": max_tokens}
    if temperature is not None:
        payload["temperature"] = temperature

    last_err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                API_URL,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {_api_key()}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://github.com/swaylq/humanize-chinese",
                    "X-Title": "humanize-chinese v6 benchmark",
                },
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.load(resp)
            choices = data.get("choices") or []
            if not choices:
                raise OpenRouterError(f"no choices: {str(data)[:300]}")
            text = (choices[0].get("message", {}).get("content") or "").strip()
            if not text:
                raise OpenRouterError(
                    f"empty content (finish_reason={choices[0].get('finish_reason')})"
                )
            return text
        except Exception as exc:  # noqa: BLE001 — retry on anything transient
            last_err = exc
            if attempt < retries - 1:
                time.sleep(2 ** attempt * 3)
    raise OpenRouterError(f"{model}: {type(last_err).__name__}: {str(last_err)[:300]}")


def chat_json(model: str, prompt: str, **kwargs) -> dict:
    """chat() whose reply is expected to be a JSON object.

    Tolerates ```json fences and leading prose, which every model emits sometimes.
    """
    raw = chat(model, prompt, **kwargs)
    return parse_json_loose(raw)


def parse_json_loose(raw: str) -> dict:
    s = raw.strip()
    if s.startswith("```"):
        s = s.split("\n", 1)[1] if "\n" in s else s
        if s.rstrip().endswith("```"):
            s = s.rstrip()[:-3]
    s = s.strip()
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        start, end = s.find("{"), s.rfind("}")
        if start != -1 and end > start:
            return json.loads(s[start:end + 1])
        raise
