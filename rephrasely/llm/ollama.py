"""Local Ollama provider for manual development."""

from __future__ import annotations

import json

import requests


def rephrase_text(
    prompt: str,
    model: str = "grammar-translator-llama3.2",
    stream: bool = False,
) -> str:
    """Generate a rewrite with a local Ollama model."""
    payload = {"model": model, "prompt": prompt, "stream": stream}
    response = requests.post("http://localhost:11434/api/generate", json=payload, stream=stream, timeout=60)
    response.raise_for_status()

    if not stream:
        return response.json().get("response", "")

    output: list[str] = []
    for line in response.iter_lines(decode_unicode=True):
        if line:
            output.append(json.loads(line).get("response", ""))
    return "".join(output)
