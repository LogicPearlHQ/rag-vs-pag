from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


RESPONSES_URL = "https://api.openai.com/v1/responses"


class OpenAIError(RuntimeError):
    pass


def _extract_text(response: dict[str, Any]) -> str:
    if isinstance(response.get("output_text"), str):
        return response["output_text"]
    parts: list[str] = []
    for item in response.get("output", []):
        for content in item.get("content", []):
            text = content.get("text")
            if isinstance(text, str):
                parts.append(text)
    if parts:
        return "".join(parts)
    raise OpenAIError(f"could not find output text in OpenAI response keys={sorted(response)}")


def responses_json_schema(
    *,
    model: str,
    system: str,
    user: str,
    schema: dict[str, Any],
    schema_name: str,
    temperature: float = 0.0,
    api_key: str | None = None,
) -> dict[str, Any]:
    key = api_key or os.getenv("OPENAI_API_KEY")
    if not key:
        raise OpenAIError("OPENAI_API_KEY is not set")

    body = {
        "model": model,
        "input": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
        "text": {
            "format": {
                "type": "json_schema",
                "name": schema_name,
                "strict": True,
                "schema": schema,
            }
        },
    }
    request = urllib.request.Request(
        RESPONSES_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise OpenAIError(f"OpenAI API error {exc.code}: {detail}") from exc
    text = _extract_text(payload)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise OpenAIError(f"OpenAI response was not JSON: {text[:500]}") from exc
    return {
        "parsed": parsed,
        "raw_response_id": payload.get("id"),
        "usage": payload.get("usage", {}),
        "model": payload.get("model", model),
    }
