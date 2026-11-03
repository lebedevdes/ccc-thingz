---
name: dialectic
description: Prove and counter-prove a statement using parallel agents to eliminate confirmation bias. Use when someone says "dialectic", "prove/disprove", "stress test this claim", "is this really true", "argue both sides", or when a statement needs objective analysis from opposing viewpoints.
---

# Dialectic Analysis

Objective analysis of a statement by running two agents with opposing goals in parallel, then synthesizing findings.

## Questions in Codex

Ask one question at a time and wait for the user's answer before continuing with any step that depends on it. Prefer a blocking user-input tool supported by the current client and mode. If only an asynchronous question tool is available, pause the workflow until the answer arrives; the tool returning is not an answer. If no suitable tool is available, ask in ordinary conversation and end the turn. Do not switch to Plan mode just to ask questions.

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
