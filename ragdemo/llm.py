"""Provider-agnostic LLM interface shared by both runners.

Three backends selected by `LP_LLM_PROVIDER`:
  - anthropic  (Claude via Messages API, tool-use for JSON, prompt caching)
  - openai     (Responses API, strict JSON schema output)
  - ollama     (local via ollama Python client, format=json)

A `fake` provider is built-in for unit tests that don't need a live call.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass
class LLMConfig:
    provider: str  # "anthropic" | "openai" | "ollama" | "fake"
    model: str
    cache_system: bool = True


@runtime_checkable
class LLM(Protocol):
    def chat_json(
        self, *, system: str, user: str, schema: dict, temperature: float = 0.0
    ) -> dict: ...
    def chat_tool(
        self, *, system: str, user: str, tool: dict, temperature: float = 0.0
    ) -> dict: ...


class FakeLLM:
    """Unit-test stub. Echoes arguments so tests can assert routing."""

    def __init__(self, cfg: LLMConfig):
        self.cfg = cfg

    def chat_json(
        self, *, system: str, user: str, schema: dict, temperature: float = 0.0
    ) -> dict:
        return {"_fake": True, "system": system, "user": user, "schema_keys": list(schema.get("properties", {}).keys())}

    def chat_tool(
        self, *, system: str, user: str, tool: dict, temperature: float = 0.0
    ) -> dict:
        return {"_fake": True, "tool": tool["name"]}


def make_llm(cfg: LLMConfig) -> LLM:
    if cfg.provider == "fake":
        return FakeLLM(cfg)
    if cfg.provider == "anthropic":
        from .llm_anthropic import AnthropicLLM

        return AnthropicLLM(cfg)
    if cfg.provider == "openai":
        from .llm_openai import OpenAILLM

        return OpenAILLM(cfg)
    if cfg.provider == "ollama":
        from .llm_ollama import OllamaLLM

        return OllamaLLM(cfg)
    raise ValueError(f"unknown provider: {cfg.provider}")
