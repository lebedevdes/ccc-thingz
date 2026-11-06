---
name: root-cause-investigator
description: Systematic root cause analysis for errors, bugs, and unexpected behaviors using 5-Why methodology. Use when user reports errors, build failures, test failures, performance issues, integration problems, or any "it's not working" scenarios.
---

# Root Cause Investigator

Apply systematic 5-Why methodology to identify fundamental root causes of issues rather than treating symptoms. Guide thorough investigation through structured evidence gathering and analysis.

## Questions in Codex

Ask one question at a time and wait for the user's answer before continuing with any step that depends on it. Respect higher-priority client instructions and use the first suitable method below:

Before selecting a question method, run `sh <skill-directory>/scripts/question-environment.sh` (resolve `<skill-directory>` to the directory containing this SKILL.md). Read its JSON output. The script cannot detect client-provided tools: check the tools actually exposed in the current client and mode. Use the reported environment IDs to address the current session and window. A failed connection is specific to the execution context; do not bypass its restrictions.

1. **For every single-choice question, use `agtermctl pick` first when the script reports a candidate.** This is required, not merely a preference: do not choose a client question tool or ordinary conversation just because it is easier or already available. Pass the reported socket and window explicitly; consult the agterm skill or `agtermctl pick open --help` for syntax. Supply every option, allow a custom answer when appropriate, and wait for the actual result. If the picker fails because of a sandbox restriction or a likely sandbox-related socket access error, retry the same picker using the shell tool's elevated-permission request, with a clear justification, before falling back. Follow the client permission policy; do not bypass restrictions or retry after approval is denied. Use the next method only if the picker is unavailable, escalation is unavailable or denied, or the picker fails after the applicable retry. A cancellation is not a choice; do not treat it as an answer. Do not target an unrelated window.
2. Use a user-input form supported by the current client and mode that can represent the question and all its choices. Prefer blocking input; if asynchronous, wait for the actual answer, not merely the tool's return.
3. Ask in ordinary conversation, presenting numbered choices where applicable, and end the turn to wait for an answer.

Do not switch to Plan mode just to ask questions.

Reuse decisions and authorization already supplied; ask only about unresolved choices.

## Activation Triggers

- errors, bugs, or unexpected behavior
- build failures or test failures
- performance issues or degradation
- integration problems
- any "it's not working" scenarios

## The 5-Why Methodology

Systematically ask "why" five times to drill down to root cause:

1. **Why #1**: identify immediate cause (symptoms)
2. **Why #2**: uncover process/workflow issues
3. **Why #3**: find system-level problems
4. **Why #4**: discover design/architecture issues
5. **Why #5**: reveal fundamental root cause

## Investigation Workflow

### 1. Gather Initial Context

Collect information about the issue:

```
## Issue Summary
[brief description of reported problem]

## Initial Symptoms
- what user is experiencing
- error messages or logs
- observable behavior

## Context Gathering
- environment details
- recent changes
- related components
- steps to reproduce
```

### 2. Apply 5-Why Analysis

Structure the investigation with progressive depth:

```
## 5-Why Analysis

### Why #1: [surface cause]
Evidence: [logs, errors, behavior]
Impact: [what this affects]

### Why #2: [deeper cause]
Evidence: [code, configuration]
Impact: [cascading effects]

### Why #3: [system cause]
Evidence: [architecture, dependencies]
Impact: [broader implications]

### Why #4: [process/design cause]
Evidence: [patterns, decisions]
Impact: [long-term effects]

### Why #5: [root cause]
Evidence: [fundamental issue]
Impact: [core problem]
```

### 3. Identify Root Cause

Document the fundamental issue requiring attention:

```
## Root Cause Identified
[the fundamental issue that needs addressing]

## Recommended Investigation Areas
- specific files to examine
- components to test
- systems to verify
```

## Investigation Principles

1. **Avoid solution bias** - focus on understanding before fixing
2. **Gather evidence** - don't assume, verify with data
3. **Consider multiple causes** - issues often have multiple contributing factors
4. **Document findings** - clear documentation prevents repeat issues
5. **Think systemically** - consider broader implications
6. **Question assumptions** - challenge "it should work" thinking
7. **Use version control** - check when issue was introduced

## Using Reference Materials

Load reference files as needed during investigation:

- **references/patterns.md** - common root cause patterns by category (configuration, race conditions, resource exhaustion, integration failures, build/deployment issues)
- **references/techniques.md** - investigation techniques with command examples (error analysis, code investigation, dependency analysis, environment investigation)

## Best Practices

- resist proposing solutions until root cause is identified
- be thorough and methodical
- document evidence at each level of analysis
- verify assumptions with concrete data
- consider the issue from multiple perspectives (technical, environmental, architectural, external dependencies, process)

The goal is to find the fundamental cause, not just fix symptoms.
