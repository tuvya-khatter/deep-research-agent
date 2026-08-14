"""The Grounding Gate — a proposed AI-DLC lifecycle stage.

Runs between Code Generation and Build & Test. It answers the one question AI-DLC's
existing gates cannot: do the generated code's assumptions about contracts it does NOT
own actually match reality?

Three stages, one human-approved checkpoint, one emitted artifact (grounding-ledger.md):

  1. BOUNDARY EXTRACTION   — list every point the code consumes an external contract.
  2. CONTRACT VERIFICATION — check each ASSUMED shape against a SOURCE OF TRUTH that is
                             NOT the model: installed type stubs, or a recorded-real
                             response captured by one live call.
  3. REALITY FIXTURE TEST  — run the extractor against a recorded-real fixture (an outside
                             witness), never a model-authored mock.

This file is generic in spirit — it knows only "boundaries", "sources of truth", and
"recorded-real fixtures". The specific boundaries below are the ones extracted from
deep_research_agent/agent.py, used here as the worked example.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

REPO = Path(__file__).resolve().parent.parent
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "sources_real.json"
LEDGER_OUT = REPO / "aidlc-docs" / "construction" / "grounding" / "grounding-ledger.md"


@dataclass
class Boundary:
    id: str
    location: str
    external_symbol: str
    assumed: str            # what the generated code assumes
    reality: str = ""       # filled by Stage 2 from a non-model source of truth
    grounded: bool = False


# ── STAGE 1 — BOUNDARY EXTRACTION (AI-assisted; the boundaries found in agent.py) ────────
def extract_boundaries() -> list[Boundary]:
    return [
        Boundary("B1", "agent._extract_sources", "strands AgentResult",
                 assumed='result.messages  (result carries full history)'),
        Boundary("B2", "agent._extract_sources", "Bedrock Converse content block",
                 assumed='block["type"] == "tool_result"  (Anthropic Messages format)'),
        Boundary("B3", "agent._parse_sources", "Tavily tool response",
                 assumed='every tool returns {"results": [...]}'),
    ]


# ── STAGE 2 — CONTRACT VERIFICATION (source of truth = installed types + recorded-real) ──
def verify_contracts(boundaries: list[Boundary], real_messages: list) -> None:
    for b in boundaries:
        if b.id == "B1":
            # Source of truth: the installed Strands AgentResult dataclass itself.
            from strands.agent.agent_result import AgentResult
            fields = set(AgentResult.__dataclass_fields__)
            has_messages = "messages" in fields
            b.reality = f'AgentResult fields = {sorted(fields)}; has "messages"? {has_messages}'
            b.grounded = has_messages  # assumption is "result.messages" → grounded only if it exists

        elif b.id == "B2":
            # Source of truth: the recorded-real response's actual block keys.
            keys = set()
            for m in real_messages:
                for blk in m.get("content", []):
                    if isinstance(blk, dict):
                        keys |= set(blk.keys())
            has_type = "type" in keys
            b.reality = f'real block keys = {sorted(keys)}; has "type"? {has_type}'
            b.grounded = has_type  # assumption matches on "type" key → grounded only if present

        elif b.id == "B3":
            # Source of truth: the tool wrappers' actual response keys (scanned from source).
            src = (REPO / "deep_research_agent" / "tools" / "tavily_tools.py").read_text()
            real_keys = set(re.findall(r'json\.dumps\(\s*\{\s*"(\w+)"', src))
            assumed_keys = {"results"}
            b.reality = f'tools emit collections {sorted(real_keys)}; code handles {sorted(assumed_keys)}'
            b.grounded = assumed_keys >= real_keys  # grounded only if code covers all real keys


# ── STAGE 3 — REALITY FIXTURE TEST (outside witness; never a model-authored mock) ────────
def reality_test(extractor, real_messages: list) -> int:
    """Run an extractor against the recorded-real history; return sources found."""
    result = SimpleNamespace(messages=real_messages)   # mimic what the ORIGINAL code expects
    try:
        return len(extractor(result))
    except Exception:
        return 0


def emit_ledger(boundaries: list[Boundary], real_n: int, orig_n: int, fixed_n: int, blocked: bool) -> None:
    LEDGER_OUT.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Grounding Ledger — deep_research_agent/agent.py",
        "",
        "*Emitted by the Grounding Gate (Construction → between Code Generation and Build & Test).*",
        "*Source of truth is never the model: installed type stubs + one recorded-real response.*",
        "",
        "## Boundaries",
        "",
        "| # | Location | Assumed (generated code) | Reality (source of truth) | Verdict |",
        "|---|---|---|---|---|",
    ]
    for b in boundaries:
        verdict = "✅ GROUNDED" if b.grounded else "🔴 DIVERGENT"
        lines.append(f"| {b.id} | `{b.location}` | {b.assumed} | {b.reality} | {verdict} |")
    lines += [
        "",
        "## Reality fixture test",
        "",
        f"- Recorded-real fixture: `grounding/fixtures/sources_real.json` — **{real_n} real sources**",
        f"- Original AI-generated extractor → **{orig_n} sources**  {'❌ FAIL' if orig_n != real_n else '✅'}",
        f"- Grounded (fixed) extractor → **{fixed_n} sources**  {'✅ PASS' if fixed_n == real_n else '❌'}",
        "",
        f"## Gate result: {'❌ BLOCKED' if blocked else '✅ PASS'}",
    ]
    LEDGER_OUT.write_text("\n".join(lines) + "\n")


def main() -> int:
    real_messages = json.loads(FIXTURE.read_text())

    # Ground truth: how many sources really exist in the recorded response.
    real_n = 0
    for m in real_messages:
        for blk in m.get("content", []):
            if isinstance(blk, dict) and "toolResult" in blk:
                for item in blk["toolResult"].get("content", []):
                    if "text" in item:
                        d = json.loads(item["text"])
                        for coll in ("results", "extractions", "pages"):
                            real_n += sum(1 for it in d.get(coll, []) if it.get("url"))

    boundaries = extract_boundaries()
    verify_contracts(boundaries, real_messages)

    from grounding.original_extractor import extract_sources_ORIGINAL
    from deep_research_agent.agent import ResearchAgent
    grounded_agent = ResearchAgent.__new__(ResearchAgent)  # no __init__; we only call pure methods

    orig_n = reality_test(extract_sources_ORIGINAL, real_messages)
    fixed_n = len(grounded_agent._extract_sources(real_messages))  # fixed code takes messages directly

    divergent = [b for b in boundaries if not b.grounded]
    blocked = bool(divergent) or orig_n != real_n
    emit_ledger(boundaries, real_n, orig_n, fixed_n, blocked)

    print("═" * 66)
    print("  GROUNDING GATE — deep_research_agent/agent.py")
    print("═" * 66)
    for b in boundaries:
        mark = "✅ GROUNDED" if b.grounded else "🔴 DIVERGENT"
        print(f"  {b.id}  {mark}")
        print(f"       assumed : {b.assumed}")
        print(f"       reality : {b.reality}")
    print("─" * 66)
    print(f"  Recorded-real fixture holds {real_n} sources")
    print(f"  Original AI-generated code → {orig_n} sources   {'❌ FAIL' if orig_n != real_n else '✅'}")
    print(f"  Grounded (fixed) code      → {fixed_n} sources   {'✅ PASS' if fixed_n == real_n else '❌'}")
    print("─" * 66)
    print(f"  GATE: {'❌ BLOCKED — ' + str(len(divergent)) + ' divergent boundaries' if blocked else '✅ PASS'}")
    print(f"  Ledger → {LEDGER_OUT.relative_to(REPO)}")
    print("═" * 66)
    return 1 if blocked else 0


if __name__ == "__main__":
    raise SystemExit(main())
