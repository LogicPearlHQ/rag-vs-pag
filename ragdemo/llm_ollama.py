"""Ollama backend: fully offline via local model, format=json."""
from __future__ import annotations

import json

import ollama

from .llm import LLMConfig


class OllamaLLM:
    def __init__(self, cfg: LLMConfig):
        self.cfg = cfg

    def chat_json(
        self, *, system: str, user: str, schema: dict, temperature: float = 0.0
    ) -> dict:
        resp = ollama.chat(
            model=self.cfg.model,
            format="json",
            options={"temperature": temperature},
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"{system}\n\n"
                        f"Respond with ONE JSON object matching this schema:\n{json.dumps(schema)}"
                    ),
                },
                {"role": "user", "content": user},
            ],
        )
        return json.loads(resp["message"]["content"])

    def chat_tool(
        self, *, system: str, user: str, tool: dict, temperature: float = 0.0
    ) -> dict:
        # Ollama's tool-use is uneven across models; treat the tool's
        # input_schema as a JSON target and fall through to chat_json.
        schema = tool["input_schema"]
        return self.chat_json(
            system=f"{system}\n\nReturn the arguments for tool `{tool['name']}`.",
            user=user,
            schema=schema,
            temperature=temperature,
        )
