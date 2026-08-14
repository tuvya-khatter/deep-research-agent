"""The original AI-generated source extractor, preserved verbatim.

This is exactly what AI-DLC's Code Generation stage produced (from
~/Downloads/aidlc-rules/deep-research-agent). It is kept here, unchanged, as the
"before" specimen the Grounding Gate is demonstrated against — do not fix it.

Every gate in the original run passed with this code in place. It never returned a
single source on a real Bedrock run.
"""

from __future__ import annotations

import json
from typing import Any


def extract_sources_ORIGINAL(result: Any) -> list[dict]:
    """Verbatim original _extract_sources logic (returns dicts instead of Source for isolation)."""
    sources: list[dict] = []
    try:
        for msg in getattr(result, "messages", []):          # ASSUMPTION: result has .messages
            for block in msg.get("content", []):
                if block.get("type") == "tool_result":       # ASSUMPTION: Anthropic block format
                    for inner in block.get("content", []):
                        if inner.get("type") == "text":
                            text = inner.get("text", "")
                            sources.extend(_parse_ORIGINAL(text))
    except Exception:
        pass
    return sources


def _parse_ORIGINAL(text: str) -> list[dict]:
    out: list[dict] = []
    try:
        data = json.loads(text)
        for item in data.get("results", []):                 # ASSUMPTION: every tool returns "results"
            url = item.get("url", "")
            if url:
                out.append({"url": url, "title": item.get("title", url)})
    except Exception:
        pass
    return out
