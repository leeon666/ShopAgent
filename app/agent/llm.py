"""OpenAI 兼容接口封装；无 Key 时返回 None，由规则引擎兜底。"""
from __future__ import annotations

import json
import re

import httpx

from ..config import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL


def _request(
    messages: list[dict],
    timeout_seconds: float = 20.0,
    response_format: dict | None = None,
) -> dict | None:
    if not OPENAI_API_KEY:
        return None
    url = OPENAI_BASE_URL.rstrip("/") + "/chat/completions"
    payload = {
        "model": OPENAI_MODEL,
        "messages": messages,
        "temperature": 0.2,
    }
    if response_format:
        payload["response_format"] = response_format
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
    try:
        with httpx.Client(timeout=timeout_seconds) as client:
            response = client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            return {
                "content": data["choices"][0]["message"]["content"],
                "usage": data.get("usage", {}),
                "model": data.get("model", OPENAI_MODEL),
            }
    except Exception:
        return None


def complete_text(system_prompt: str, user_prompt: str, timeout_seconds: float = 20.0) -> str | None:
    result = _request(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        timeout_seconds=timeout_seconds,
    )
    return result["content"] if result else None


def complete_json(
    system_prompt: str,
    user_prompt: str,
    timeout_seconds: float = 20.0,
) -> dict | None:
    result = _request(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        timeout_seconds=timeout_seconds,
        response_format={"type": "json_object"},
    )
    if not result:
        return None
    content = result["content"].strip()
    content = re.sub(r"^```(?:json)?\s*", "", content)
    content = re.sub(r"\s*```$", "", content)
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    return {"data": parsed, "usage": result.get("usage", {}), "model": result.get("model")}
