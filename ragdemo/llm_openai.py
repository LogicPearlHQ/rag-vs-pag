"""OpenAI backend: Chat Completions with strict JSON schema + function tool-use."""
from __future__ import annotations

import json

from openai import OpenAI

from .llm import LLMConfig


class OpenAILLM:
    def __init__(self, cfg: LLMConfig):
        self.cfg = cfg
        self.client = OpenAI()  # reads OPENAI_API_KEY from env

    def chat_json(
        self, *, system: str, user: str, schema: dict, temperature: float = 0.0
    ) -> dict:
        resp = self.client.chat.completions.create(
            model=self.cfg.model,
            temperature=temperature,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "answer",
                    "schema": schema,
                    "strict": True,
                },
            },
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        content = resp.choices[0].message.content or "{}"
        return json.loads(content)

    def chat_tool(
        self, *, system: str, user: str, tool: dict, temperature: float = 0.0
    ) -> dict:
        resp = self.client.chat.completions.create(
            model=self.cfg.model,
            temperature=temperature,
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool.get("description", ""),
                        "parameters": tool["input_schema"],
                        "strict": True,
                    },
                }
            ],
            tool_choice={"type": "function", "function": {"name": tool["name"]}},
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        choice = resp.choices[0].message
        if not choice.tool_calls:
            raise RuntimeError("openai: no tool_calls in response")
        return json.loads(choice.tool_calls[0].function.arguments)
