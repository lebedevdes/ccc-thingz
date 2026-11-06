---
name: dialectic
description: Prove and counter-prove a statement using parallel agents to eliminate confirmation bias. Use when someone says "dialectic", "prove/disprove", "stress test this claim", "is this really true", "argue both sides", or when a statement needs objective analysis from opposing viewpoints.
---

# Dialectic Analysis

Objective analysis of a statement by running two agents with opposing goals in parallel, then synthesizing findings.

## Questions in Codex

Ask one question at a time and wait for the user's answer before continuing with any step that depends on it. Respect higher-priority client instructions and use the first suitable method below:

Before selecting a question method, run `sh <skill-directory>/scripts/question-environment.sh` (resolve `<skill-directory>` to the directory containing this SKILL.md). Read its JSON output. The script cannot detect client-provided tools: check the tools actually exposed in the current client and mode. Use the reported environment IDs to address the current session and window. A failed connection is specific to the execution context; do not bypass its restrictions.

1. **For every single-choice question, use `agtermctl pick` first when the script reports a candidate.** This is required, not merely a preference: do not choose a client question tool or ordinary conversation just because it is easier or already available. Pass the reported socket and window explicitly; consult the agterm skill or `agtermctl pick open --help` for syntax. Supply every option, allow a custom answer when appropriate, and wait for the actual result. If the picker fails because of a sandbox restriction or a likely sandbox-related socket access error, retry the same picker using the shell tool's elevated-permission request, with a clear justification, before falling back. Follow the client permission policy; do not bypass restrictions or retry after approval is denied. Use the next method only if the picker is unavailable, escalation is unavailable or denied, or the picker fails after the applicable retry. A cancellation is not a choice; do not treat it as an answer. Do not target an unrelated window.
2. Use a user-input form supported by the current client and mode that can represent the question and all its choices. Prefer blocking input; if asynchronous, wait for the actual answer, not merely the tool's return.
3. Ask in ordinary conversation, presenting numbered choices where applicable, and end the turn to wait for an answer.

Do not switch to Plan mode just to ask questions.

Reuse decisions and authorization already supplied; ask only about unresolved choices.

## Process

### Step 1: Launch Parallel Agents

**CRITICAL: Launch both agents before waiting for either result, using the available, authorized Codex subagent tools.** Wait for both to finish before synthesizing. Do not assume Claude Code's `Task` or `run_in_background` interfaces exist. If delegation or concurrent slots are unavailable, perform the two passes sequentially and state that the analysis lacks parallel independent agents.

**Agent 1 (Thesis)** — find all POSITIVE evidence:
- what works well, improvements, correct patterns
- supporting facts, proof the statement is TRUE
- benefits, strengths, successful outcomes

**Agent 2 (Antithesis)** — find all NEGATIVE evidence:
- what's problematic, issues, risks, anti-patterns
- edge cases, proof the statement is FALSE
- weaknesses, failure modes, hidden costs

Both agents must provide specific file paths and line numbers when analyzing code.

### Step 2: Synthesize

After both agents complete, synthesize findings into an objective conclusion:
- weigh evidence from both sides
- identify where thesis and antithesis agree (strongest signal)
- note unresolved tensions

### Step 3: Verify

**CRITICAL** — after presenting the synthesis, verify it against actual implementation:
- read the specific files and line numbers referenced by both agents
- confirm the evidence cited actually exists in the codebase
- check the implementation flow matches the claims made
- verify the synthesis accurately reflects the actual code context
- identify any misinterpretations or missing context from agent reports
- revise synthesis if verification reveals inaccuracies

## Use Cases

**Architecture decisions:**
```
$dialectic this microservice split improves maintainability
```

**Bug analysis:**
```
$dialectic the connection pool fixes the timeout issue
```

**Performance claims:**
```
$dialectic caching reduced database load by 80%
```

**Refactoring safety:**
```
$dialectic extracting this interface simplifies testing
```

**Code review:**
```
$dialectic this implementation is thread-safe
```

**Review changes:**
```
$dialectic review the changes in server.go
```

## Key Principles

- **Eliminate confirmation bias** — examining both sides simultaneously prevents anchoring on the first conclusion
- **Evidence-based** — agents must cite specific files, lines, and facts, not general claims
- **Verification required** — synthesis must be checked against actual code before presenting
- **Objective conclusion** — the goal is truth, not winning either side
