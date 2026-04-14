"""Anthropic backend: Claude Messages API with tool-use JSON + prompt caching."""
from __future__ import annotations

from anthropic import Anthropic

from .llm import LLMConfig


class AnthropicLLM:
    def __init__(self, cfg: LLMConfig):
        self.cfg = cfg
        self.client = Anthropic()  # reads ANTHROPIC_API_KEY from env

    def _system_blocks(self, system: str) -> list[dict]:
        block: dict = {"type": "text", "text": system}
        if self.cfg.cache_system:
            block["cache_control"] = {"type": "ephemeral"}
        return [block]

    def chat_json(
        self, *, system: str, user: str, schema: dict, temperature: float = 0.0
    ) -> dict:
        # Enforce JSON by defining a single tool whose input_schema is the
        # target schema and forcing tool_choice to that tool.
        tool = {
            "name": "emit",
            "description": "Return the requested answer.",
            "input_schema": schema,
        }
        resp = self.client.messages.create(
            model=self.cfg.model,
            max_tokens=4096,
            temperature=temperature,
            system=self._system_blocks(system),
            tools=[tool],
            tool_choice={"type": "tool", "name": "emit"},
            messages=[{"role": "user", "content": user}],
        )
        for block in resp.content:
            if getattr(block, "type", None) == "tool_use" and block.name == "emit":
                return dict(block.input)
        raise RuntimeError("anthropic: no tool_use block in response")

    def chat_tool(
        self, *, system: str, user: str, tool: dict, temperature: float = 0.0
    ) -> dict:
        resp = self.client.messages.create(
            model=self.cfg.model,
            max_tokens=4096,
            temperature=temperature,
            system=self._system_blocks(system),
            tools=[tool],
            tool_choice={"type": "tool", "name": tool["name"]},
            messages=[{"role": "user", "content": user}],
        )
        for block in resp.content:
            if getattr(block, "type", None) == "tool_use" and block.name == tool["name"]:
                return dict(block.input)
        raise RuntimeError(f"anthropic: no tool_use {tool['name']} in response")
