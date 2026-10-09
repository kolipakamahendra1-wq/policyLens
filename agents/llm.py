"""Minimal client for any OpenAI-compatible chat endpoint (free models only:
local Ollama by default, or a free OpenRouter model via env vars)."""
import json

import httpx

from backend.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, LLM_TIMEOUT


def chat_json(system: str, user: str) -> dict:
    r = httpx.post(
        f"{LLM_BASE_URL.rstrip('/')}/chat/completions",
        headers={"Authorization": f"Bearer {LLM_API_KEY}"},
        json={
            "model": LLM_MODEL,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        },
        timeout=LLM_TIMEOUT,
    )
    r.raise_for_status()
    content = r.json()["choices"][0]["message"]["content"]
    return json.loads(content)
