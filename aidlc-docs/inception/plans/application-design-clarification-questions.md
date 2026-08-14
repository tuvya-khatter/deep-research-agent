# Application Design Clarification Questions

One contradiction was detected that needs resolving before artifacts can be generated.

---

## Contradiction: Who triggers OutputManager? (Q5 vs Q6)

**Q5** — You chose **A: Pipeline service**:
> "A `ResearchPipeline` service owns the end-to-end flow: invokes the agent, captures streamed output, **triggers file write**, and records to log"

**Q6** — You chose **C: CLI triggers OutputManager**:
> "Called by the CLI after each query completes — CLI receives the full response from the agent and passes it to OutputManager"

These conflict: Q5 says `ResearchPipeline` is responsible for triggering the file write, while Q6 says the `CLI` calls `OutputManager` directly.

---

### Clarification Question 1
Who owns the responsibility of invoking `OutputManager` after a research run?

A) `ResearchPipeline` — the pipeline service runs the full flow (agent invocation → file write → logging); the CLI only calls `pipeline.run(query)` and handles streaming display
B) `CLI` — the CLI calls the agent, receives the completed response, then calls `OutputManager` directly; no separate pipeline service (drops Q5=A, simplifies the design)
C) Both — `ResearchPipeline` handles agent invocation and logging; `CLI` receives the streamed response from the pipeline and then calls `OutputManager` with the final text
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

Please fill in the `[Answer]:` tag and let me know when done.
