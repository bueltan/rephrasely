"""xAI Grok provider."""

from __future__ import annotations

import json
import os
import sys
from typing import Any

import requests

XAI_CHAT_URL = "https://api.x.ai/v1/chat/completions"


def grok_chat(
    messages: list[dict[str, str]],
    model: str,
    temperature: float = 0.0,
    stream: bool = False,
    timeout: int = 60,
) -> str:
    """Call the xAI chat completions API and return the generated text."""
    api_key = os.getenv("XAI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing XAI_API_KEY environment variable.")

    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "stream": stream,
    }
    response = requests.post(
        XAI_CHAT_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        stream=stream,
        timeout=timeout,
    )

    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        raise requests.HTTPError(
            f"HTTP Error: {exc}. Response: {response.text}"
        ) from exc

    if not stream:
        data = response.json()
        return data["choices"][0]["message"]["content"]

    output: list[str] = []
    for raw_line in response.iter_lines(decode_unicode=True):
        if not raw_line:
            continue

        line = raw_line.strip()
        if line.startswith("data:"):
            line = line[len("data:") :].strip()
        if line == "[DONE]":
            break

        try:
            obj = json.loads(line)
            delta = obj.get("choices", [{}])[0].get("delta", {}).get("content", "")
        except json.JSONDecodeError:
            delta = line

        if delta:
            sys.stdout.write(delta)
            sys.stdout.flush()
            output.append(delta)

    return "".join(output)


def rephrase_text(prompt: str, model: str = "grok-3-mini-fast", stream: bool = False) -> str:
    """Translate to natural English or improve English clarity while preserving meaning."""
    system_prompt = (
        "You are a precise translator and editor. "
        "Task: translate the user's text to clear, natural English and improve grammar, "
        "tone, and flow while preserving meaning. If the input is already in English, "
        "just improve clarity and correctness. Return only the improved text."
    )

    return grok_chat(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        model=model,
        temperature=0,
        stream=stream,
    )
