"""The reality-fixture test — the heart of the Grounding Gate.

Unlike the original AI-authored tests (which mocked `result.messages = []` — a mock built
from the same wrong assumption as the code), these run against a RECORDED-REAL response
captured from a live Bedrock + Tavily run (grounding/fixtures/sources_real.json).

A recorded-real fixture is an outside witness: it cannot share the model's blind spot.
That is the whole point of grounding.

  - The original AI-generated extractor FAILS it (0 sources).
  - The grounded (fixed) extractor PASSES it (the real source count).
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from deep_research_agent.agent import ResearchAgent
from grounding.original_extractor import extract_sources_ORIGINAL

_FIXTURE = Path(__file__).resolve().parent.parent / "grounding" / "fixtures" / "sources_real.json"


def _real_messages() -> list:
    return json.loads(_FIXTURE.read_text())


def _real_source_count(messages: list) -> int:
    """Ground truth: how many URLs the recorded response actually contains."""
    n = 0
    for m in messages:
        for blk in m.get("content", []):
            if isinstance(blk, dict) and "toolResult" in blk:
                for item in blk["toolResult"].get("content", []):
                    if "text" in item:
                        d = json.loads(item["text"])
                        for coll in ("results", "extractions", "pages"):
                            n += sum(1 for it in d.get(coll, []) if it.get("url"))
    return n


def _fixed_agent() -> ResearchAgent:
    mock_tool = SimpleNamespace(as_strands_tool=lambda: None)
    with patch("deep_research_agent.agent.Agent"), patch("deep_research_agent.agent.BedrockModel"):
        return ResearchAgent(model_id="x", tools=[mock_tool])


def test_fixture_has_real_sources() -> None:
    """Sanity: the recorded-real fixture genuinely contains sources to find."""
    assert _real_source_count(_real_messages()) > 0


def test_original_ai_generated_code_FAILS_reality() -> None:
    """The code AI-DLC shipped returns 0 against a real response — the bug that passed every old gate."""
    messages = _real_messages()
    # Give the original its assumed shape (result.messages) so we isolate the FORMAT bug specifically:
    # even handed a valid history, it still finds nothing because it matches block["type"], not "toolResult".
    result = SimpleNamespace(messages=messages)
    assert len(extract_sources_ORIGINAL(result)) == 0


def test_grounded_code_PASSES_reality() -> None:
    """The fixed extractor recovers exactly the real sources from the recorded response."""
    messages = _real_messages()
    expected = _real_source_count(messages)
    got = _fixed_agent()._extract_sources(messages)
    assert len(got) == expected
    assert all(s.url for s in got)
