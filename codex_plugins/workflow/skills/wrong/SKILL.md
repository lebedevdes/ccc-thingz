---
name: wrong
description: Reset and re-evaluate when current approach isn't working. Use when user says "wrong", "this isn't working", "wrong approach", "start over", "try again", "bad direction", or when the current solution path has hit a dead end and needs a fresh perspective.
---

# Wrong — Reset and Re-evaluate

The current approach isn't working as expected. Step back and re-examine the problem from the beginning.

## Questions in Codex

Ask one question at a time and wait for the user's answer before continuing with any step that depends on it. Respect higher-priority client instructions and use the first suitable method below:

Before selecting a question method, run `sh <skill-directory>/scripts/question-environment.sh` (resolve `<skill-directory>` to the directory containing this SKILL.md). Read its JSON output. The script cannot detect client-provided tools: check the tools actually exposed in the current client and mode. Use the reported environment IDs to address the current session and window. A failed connection is specific to the execution context; do not bypass its restrictions.

1. **For every single-choice question, use `agtermctl pick` first when the script reports a candidate.** This is required, not merely a preference: do not choose a client question tool or ordinary conversation just because it is easier or already available. Pass the reported socket and window explicitly; consult the agterm skill or `agtermctl pick open --help` for syntax. Supply every option, allow a custom answer when appropriate, and wait for the actual result. If the picker fails because of a sandbox restriction or a likely sandbox-related socket access error, retry the same picker using the shell tool's elevated-permission request, with a clear justification, before falling back. Follow the client permission policy; do not bypass restrictions or retry after approval is denied. Use the next method only if the picker is unavailable, escalation is unavailable or denied, or the picker fails after the applicable retry. A cancellation is not a choice; do not treat it as an answer. Do not target an unrelated window.
2. Use a user-input form supported by the current client and mode that can represent the question and all its choices. Prefer blocking input; if asynchronous, wait for the actual answer, not merely the tool's return.
3. Ask in ordinary conversation, presenting numbered choices where applicable, and end the turn to wait for an answer.

Do not switch to Plan mode just to ask questions.

Reuse decisions and authorization already supplied; ask only about unresolved choices.

## Workflow

### Step 1: Re-analyze the Core Problem

State the problem in clear, simple terms. What exactly are we trying to solve?

### Step 2: Identify Missing Context

Determine what additional information is needed about:
- The existing codebase and its patterns
- Performance requirements or constraints
- Integration points with other systems
- Expected usage patterns or scale
- Any domain-specific requirements not yet mentioned

### Step 3: Propose Fresh Approaches

Suggest 2-3 alternative solutions that:
- Follow project best practices and idioms
- Match the existing code's style and architecture patterns
- Are maintainable and testable
- Solve the exact problem without over-engineering
- Don't use shortcuts or hacks

### Step 4: Explain Trade-offs

For each proposed approach, briefly explain:
- Why this approach fits the problem
- What the main benefits and drawbacks are
- How it integrates with the existing codebase

### Step 5: Recommend the Best Path Forward

Which approach is most appropriate and why?

## Requirements

- Solution must be production-ready, not a proof of concept
- Code should be idiomatic and follow established patterns
- Include comprehensive tests with edge cases
- Provide complete, runnable code with no placeholders
- Ensure the solution is maintainable

**Ask clarifying questions before proceeding.**
