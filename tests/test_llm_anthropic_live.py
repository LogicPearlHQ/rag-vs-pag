import os

import pytest

pytestmark = pytest.mark.live


@pytest.mark.skipif(not os.getenv("ANTHROPIC_API_KEY"), reason="no ANTHROPIC_API_KEY")
def test_anthropic_json_roundtrip():
    from ragdemo.llm import LLMConfig, make_llm

    llm = make_llm(LLMConfig(provider="anthropic", model="claude-opus-4-6"))
    out = llm.chat_json(
        system="You return JSON.",
        user='Return {"ok": true}',
        schema={
            "type": "object",
            "properties": {"ok": {"type": "boolean"}},
            "required": ["ok"],
        },
    )
    assert out["ok"] is True
