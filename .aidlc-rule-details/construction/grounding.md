# Grounding

**Purpose**: Verify that generated code's assumptions about contracts it does not own match reality, before those assumptions are baked into a self-authored test suite.

**Motivation**: AI-DLC's existing gates confirm two things — that the specification is self-consistent (contradiction detection) and that every rule was addressed in code (traceability). Neither can confirm that the code is *correct at runtime*. When the same model writes both the code and its tests, a wrong assumption about an external contract (an SDK's response shape, an API's message format, a data schema) is encoded identically in both — so the test agrees with the bug instead of catching it. Grounding closes this gap by checking assumptions against a source of truth that is **never the model**.

## Prerequisites
- Code Generation must be complete for the unit
- All generated code artifacts must be available
- External dependencies must be installed (their type stubs are a source of truth)
- Credentials/config sufficient to capture ONE real response from each external service

## Position in Lifecycle
Executes in the CONSTRUCTION phase, **after Code Generation and before Build and Test**. It must run before Build and Test because the test suite generated there would otherwise inherit the same unverified assumptions as the code.

---

## Step 1: Boundary Extraction

Identify every point where the generated code consumes a contract it does **not own**.

- [ ] Scan generated code for boundary points:
  - Calls into third-party SDKs / external APIs
  - Parsing of responses returned by external services
  - Attribute or key access on objects returned by external libraries
  - Assumptions about file, wire, or serialization formats
- [ ] For each boundary, record: `location`, `external_symbol`, and the `assumed` shape the code depends on
- [ ] Write these rows into `aidlc-docs/construction/grounding/grounding-ledger.md` (Boundaries table)

## Step 2: Contract Verification

For each boundary, check the assumed shape against a **source of truth**, in strict priority order. **Never use the model's own knowledge as the source of truth.**

- [ ] Source of truth priority:
  1. The installed dependency's own type stubs / schema (inspect the package, do not recall it)
  2. A recorded-real response captured by making ONE live call to the dependency
  3. Official published schema (OpenAPI, JSON Schema, protobuf)
- [ ] Mark each boundary **GROUNDED** (assumption matches reality) or **DIVERGENT** (it does not)
- [ ] Record the reality evidence for each boundary in the ledger
- [ ] **Critical**: a DIVERGENT boundary is a blocking finding — it MUST be resolved before this gate passes

## Step 3: Reality Fixture Synthesis

Replace mocks-of-what-you-don't-own with fixtures captured from reality.

- [ ] Capture at least one recorded-real response per external service and commit it under `grounding/fixtures/`
- [ ] For each boundary, write at least one test that runs against the recorded-real fixture — **not** a model-authored mock
- [ ] Add anti-silent-failure assertions (e.g. "after tool calls occurred, extracted results MUST be > 0")
- [ ] Forbid `except Exception: pass` around boundary parsing — a boundary failure must surface, never return empty silently

## Step 4: Emit Ledger and Gate

- [ ] Finalize `aidlc-docs/construction/grounding/grounding-ledger.md` with:
  - The Boundaries table (assumed vs reality vs verdict)
  - The reality-fixture test outcomes
  - The overall gate result
- [ ] Update `aidlc-docs/aidlc-state.md`: mark Grounding COMPLETE only if the gate passed
- [ ] Present the ledger to the human for approval

---

## Critical Rules

- **RULE-GND-01**: The source of truth for any contract is never the model. Use installed type stubs, a recorded-real response, or a published schema — in that order.
- **RULE-GND-02**: Reality-fixture tests MUST run against captured real responses, never mocks the model authored. A mock built from the same assumption as the code cannot falsify that assumption.
- **RULE-GND-03**: Any DIVERGENT boundary is a blocking finding. The gate does not pass — and Build and Test does not begin — until every boundary is GROUNDED or explicitly waived by the human with a recorded rationale.
- **RULE-GND-04**: Boundary parsing MUST NOT swallow exceptions into an empty result. "Zero results after a successful external call" MUST be treated as an error signal, not a valid outcome.
- **RULE-GND-05**: Grounding validates code against external reality only. It does NOT validate that the specification matches intent (that is contradiction detection's role) and does NOT catch pure business-logic errors with no external contract.

## Gate Condition
This gate PASSES only when every extracted boundary is GROUNDED (or human-waived) **and** every boundary has a passing recorded-real fixture test. Otherwise the gate is BLOCKED and the lifecycle does not advance to Build and Test.
