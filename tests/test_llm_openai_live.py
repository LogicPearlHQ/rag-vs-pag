import os

import pytest

pytestmark = pytest.mark.live


@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="no OPENAI_API_KEY")
def test_openai_json_roundtrip():
    from ragdemo.llm import LLMConfig, make_llm

    llm = make_llm(LLMConfig(provider="openai", model="gpt-4o-mini"))
    out = llm.chat_json(
        system="You return JSON.",
        user='Return {"ok": true}',
        schema={
            "type": "object",
            "properties": {"ok": {"type": "boolean"}},
            "required": ["ok"],
            "additionalProperties": False,
        },
    )
    assert out["ok"] is True
