"""OpenAI 兼容接口封装；无 Key 时返回 None，由规则引擎兜底。"""
from __future__ import annotations

import httpx

from ..config import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL


def complete_text(system_prompt: str, user_prompt: str, timeout_seconds: float = 20.0) -> str | None:
    if not OPENAI_API_KEY:
        return None
    url = OPENAI_BASE_URL.rstrip("/") + "/chat/completions"
    payload = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
    }
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
    try:
        with httpx.Client(timeout=timeout_seconds) as client:
            response = client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
    except Exception:
        return None
