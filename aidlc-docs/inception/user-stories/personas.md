# User Personas

## Overview

Two domain-based personas serve the Deep Research Agent CLI. Both share the same interface but differ in technical comfort, customization needs, and how they interpret and use research output.

---

## Persona 1: Alex — The Technical Researcher

**Domain**: Technical (software developer, data scientist, technical analyst, AI/ML engineer)

### Profile
- Comfortable operating in a terminal environment
- Understands AWS credential configuration, IAM roles, and environment variables
- Familiar with LLM concepts (models, tokens, latency trade-offs)
- Uses the agent as part of a larger workflow — may pipe output into other tools or scripts
- Wants to inspect logs to understand what the agent did and diagnose issues

### Goals
- Quickly gather deep technical information on a topic (libraries, APIs, papers, benchmarks)
- Evaluate the agent's behavior and cost profile for potential integration into broader workflows
- Understand exactly which sources were used and how the research was structured
- Run multiple queries in a session without context switching

### Pain Points
- Opaque errors with no actionable guidance
- Inability to control which model is used (cost/capability trade-off matters)
- Slow startup or long waits before seeing any output
- Output files that don't clearly cite sources or include metadata

### Interactions with the Agent
- Launches with `--model` flag to select a specific Bedrock model
- Specifies `--output-dir` to route files to a project folder
- Reviews log file after sessions to check token usage and latency
- Exits session with `Ctrl+C` or `exit` command

### Relevant User Stories
US-001, US-002, US-003, US-004, US-005, US-006, US-007, US-008, US-009, US-010, US-011, US-012, US-013

---

## Persona 2: Morgan — The Business Analyst / Knowledge Worker

**Domain**: Business (management consultant, business analyst, strategy researcher, policy analyst)

### Profile
- Uses a terminal but prefers working with defaults rather than configuring parameters
- Focused on the quality and credibility of research output rather than technical mechanics
- Produces deliverables for stakeholders — reports, briefings, memos
- Needs to trust the output is thorough and well-sourced before sharing it externally
- Less likely to inspect log files; more likely to review the Markdown output carefully

### Goals
- Get a comprehensive, well-structured research summary on a business or policy topic
- Verify that the output is backed by credible, citable sources
- Save results as a Markdown file to paste into reports or share with colleagues
- Complete multiple research tasks in one sitting without restarting the tool

### Pain Points
- Output that lacks source citations or has uncited claims
- Crashes or silent failures mid-research with no clear explanation
- Output files with inconsistent structure that are hard to read or reformat
- No indication of whether the research was thorough or superficial

### Interactions with the Agent
- Launches the agent with default settings (no flags)
- Submits plain-language research queries
- Reviews the generated Markdown file for structure, sources, and completeness
- Exits with the `exit` command at end of session

### Relevant User Stories
US-001, US-002, US-003, US-004, US-005, US-006, US-007, US-008, US-009, US-010, US-011, US-012

---

## Persona-to-Story Mapping

| Story ID | Story Title | Alex | Morgan |
|---|---|---|---|
| US-001 | Configure Agent Credentials | Primary | Primary |
| US-002 | Start Interactive Session (with config) | Primary | Primary |
| US-003 | Submit Query with Streaming Output | Primary | Primary |
| US-004 | Run Multiple Queries in One Session | Primary | Primary |
| US-005 | Exit Session Cleanly | Primary | Primary |
| US-006 | Receive Research as Markdown File | Primary | Primary |
| US-007 | Verify Research Sources and Metadata | Secondary | Primary |
| US-008 | Handle Missing or Invalid Credentials | Primary | Primary |
| US-009 | Handle Tavily API Failure | Secondary | Primary |
| US-010 | Handle Bedrock Invocation Failure | Primary | Primary |
| US-011 | Handle Invalid or Empty Query | Primary | Primary |
| US-012 | Handle Interrupted Session | Primary | Secondary |
| US-013 | Access Research Log File | Primary | — |
