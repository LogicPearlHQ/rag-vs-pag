import pytest

from ragdemo.llm import FakeLLM, LLM, LLMConfig, make_llm


def test_fake_provider_returns_stub():
    llm = make_llm(LLMConfig(provider="fake", model="none"))
    assert isinstance(llm, LLM)
    out = llm.chat_json(system="s", user="u", schema={"type": "object", "properties": {"ok": {"type": "boolean"}}})
    assert out["_fake"] is True
    assert "ok" in out["schema_keys"]


def test_fake_tool_returns_tool_name():
    llm = make_llm(LLMConfig(provider="fake", model="none"))
    out = llm.chat_tool(system="s", user="u", tool={"name": "myTool", "input_schema": {"type": "object"}})
    assert out["tool"] == "myTool"


def test_unknown_provider_raises():
    with pytest.raises(ValueError, match="unknown provider"):
        make_llm(LLMConfig(provider="mystery", model="x"))
