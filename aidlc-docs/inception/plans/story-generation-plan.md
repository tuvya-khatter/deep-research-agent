# Story Generation Plan

## Project Context
- **Project**: Deep Research Agent CLI
- **Tech Stack**: Python 3.12, Strands Agents SDK, Amazon Bedrock, Tavily Search/Extract/Crawl
- **Key Interactions**: Interactive REPL CLI, streaming LLM output, Markdown file output per query

---

## Execution Checklist

### Phase 1 — Planning (Questions)
- [x] Step 1: Answer all questions in this document
- [x] Step 2: Resolve any ambiguities or contradictions
- [x] Step 3: Approve this plan

### Phase 2 — Generation
- [x] Step 4: Generate `aidlc-docs/inception/user-stories/personas.md`
- [x] Step 5: Generate `aidlc-docs/inception/user-stories/stories.md`
- [x] Step 6: Verify all stories meet INVEST criteria and have acceptance criteria
- [x] Step 7: Map personas to stories

---

## Story Planning Questions

Please fill in the letter choice after each `[Answer]:` tag. Choose `X` and add a description if none of the options fit.

---

### Section 1: User Personas

#### Question 1
Who is the primary user of the deep research agent?

A) Individual researcher or analyst — a single person conducting in-depth research on topics for reports, papers, or decisions
B) Developer or technical user — someone building on top of or evaluating the agent, running it from a terminal
C) Knowledge worker or consultant — someone who needs quick but thorough information gathering to support client work or decisions
D) All of the above — the agent should serve multiple distinct user types
X) Other (please describe after [Answer]: tag below)

[Answer]: D

---

#### Question 2
Should secondary personas be defined (e.g., a power user who configures model/depth vs. a casual user who accepts defaults)?

A) Yes — define at least two personas: one who uses default settings and one who customizes model/depth/output
B) No — one primary persona is sufficient; all users are treated the same
C) Yes — define personas by domain (e.g., technical researcher vs. business analyst)
X) Other (please describe after [Answer]: tag below)

[Answer]: C

---

### Section 2: Story Breakdown Approach

#### Question 3
How should user stories be organized?

A) User Journey-Based — stories follow the research workflow end-to-end (start session → enter query → watch research → review output)
B) Feature-Based — stories organized around capabilities (CLI startup, query input, Tavily tool use, LLM synthesis, file output, error handling)
C) Persona-Based — one story set per persona type
D) Epic-Based — top-level epics (Session Management, Research Execution, Output Management) broken into sub-stories
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

#### Question 4
What level of story granularity is appropriate?

A) Fine-grained — individual stories for each distinct user action or system response (e.g., one story for "stream LLM tokens to terminal", another for "display tool call status")
B) Medium-grained — stories at the feature level, each covering one meaningful capability end-to-end (e.g., "As a researcher, I can submit a query and receive a streamed research summary")
C) Coarse-grained — epics only, with sub-stories left as bullet points rather than full stories
X) Other (please describe after [Answer]: tag below)

[Answer]: B

---

### Section 3: Story Format & Acceptance Criteria

#### Question 5
What user story format should be used?

A) Classic — "As a [persona], I want [goal] so that [benefit]" with a bulleted acceptance criteria list
B) Job Story — "When [situation], I want to [motivation], so I can [outcome]" (context-first format)
C) Given-When-Then — stories expressed as BDD scenarios using Given/When/Then syntax
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

#### Question 6
How detailed should acceptance criteria be?

A) Minimal — 2–3 high-level criteria per story (e.g., "output file is created", "streaming is visible")
B) Standard — 4–6 criteria per story covering happy path and key edge cases
C) Comprehensive — full criteria including happy path, edge cases, error conditions, and performance expectations
X) Other (please describe after [Answer]: tag below)

[Answer]: C

---

### Section 4: User Journey Scope

#### Question 7
Which user journeys should be covered by stories? (Select the most important scope)

A) Core journey only — query input → research execution → Markdown file output
B) Core + session management — includes starting the REPL, running multiple queries, and exiting cleanly
C) Core + session management + error/edge cases — includes API failures, empty results, invalid inputs, and interrupted sessions
D) Full coverage — all of the above plus configuration (model selection, output directory), observability (log file), and first-run experience
X) Other (please describe after [Answer]: tag below)

[Answer]: D

---

#### Question 8
Should stories cover the agent's internal behavior visible to the user (e.g., status messages like "Searching for X…", "Extracting from Y sources…")?

A) Yes — stories should specify what progress/status the user sees during research so it is testable
B) No — internal agent behavior is an implementation detail; stories should only cover inputs and outputs
C) Partially — include progress visibility as acceptance criteria but not as separate stories
X) Other (please describe after [Answer]: tag below)

[Answer]: B

---

### Section 5: Business Context & Success Criteria

#### Question 9
What does a successful research session look like from the user's perspective?

A) The agent returns a well-structured Markdown file with cited sources within a reasonable time
B) The agent demonstrates it searched, extracted, and synthesized multiple sources — the process transparency matters as much as the output
C) The user can verify the research is thorough by reviewing the source list and metadata in the output file
D) All of the above — success requires quality output, visible process, and verifiable sources
X) Other (please describe after [Answer]: tag below)

[Answer]: C

---

#### Question 10
Should stories include any non-functional expectations (e.g., streaming latency, output file naming, log file location)?

A) Yes — include NFR expectations as acceptance criteria within relevant stories
B) No — NFRs are already captured in requirements; stories should focus on functional behavior only
C) Partially — include only user-visible NFRs (e.g., "first token appears within X seconds") but not internal ones (e.g., log rotation policy)
X) Other (please describe after [Answer]: tag below)

[Answer]: B

---

### Section 6: Technical Constraints & Edge Cases

#### Question 11
Should stories explicitly cover error scenarios and recovery paths?

A) Yes — include stories for: Tavily API failure, Bedrock invocation failure, missing API credentials, invalid query input, and interrupted session
B) Partially — cover credential errors and API failures only (highest user impact)
C) No — error handling is defined in requirements; stories should focus on happy-path interactions
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

#### Question 12
Should the configurable model selection (CLI `--model` arg) have its own story or be folded into a general "configuration" story?

A) Own story — "As a power user, I can specify the Bedrock model at launch so I can control cost vs. capability trade-offs"
B) Folded in — include model selection as an acceptance criterion within the CLI startup story
C) Not needed as a story — model selection is a technical parameter, not a user story
X) Other (please describe after [Answer]: tag below)

[Answer]: C

---

## Story Breakdown Options

Once questions are answered, stories will be generated using one of these approaches (determined by Q3):

| Approach | Description | Best For |
|---|---|---|
| User Journey-Based | Stories follow the research workflow step by step | Clear, linear interactions |
| Feature-Based | One story per capability cluster | Systems with independent features |
| Persona-Based | Story set per persona type | Multi-user-type systems |
| Epic-Based | Hierarchical epics with sub-stories | Complex systems needing hierarchy |

---

## Instructions

1. Fill in every `[Answer]:` tag above with your letter choice
2. If you choose `X`, add your custom response on the same line after the tag
3. Save the file and let me know when done — I will review for ambiguities before generating stories
