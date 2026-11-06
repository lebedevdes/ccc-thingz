---
name: ask-opencode
description: Consult OpenCode for investigation, debugging, or code review. Use when user explicitly asks to "ask opencode", "check with opencode", "opencode review", or as a last resort when stuck after 4+ failed attempts at debugging, investigation, or bug fix and completely out of ideas. Only escalate automatically when truly stuck. OpenCode runs with read/search access to the project — it analyzes, Codex implements.
---

# Ask OpenCode

Consult OpenCode as a second opinion for investigation, debugging, or review tasks.

## Questions in Codex

Ask one question at a time and wait for the user's answer before continuing with any step that depends on it. Respect higher-priority client instructions and use the first suitable method below:

Before selecting a question method, run `sh <skill-directory>/scripts/question-environment.sh` (resolve `<skill-directory>` to the directory containing this SKILL.md). Read its JSON output. The script cannot detect client-provided tools: check the tools actually exposed in the current client and mode. Use the reported environment IDs to address the current session and window. A failed connection is specific to the execution context; do not bypass its restrictions.

1. **For every single-choice question, use `agtermctl pick` first when the script reports a candidate.** This is required, not merely a preference: do not choose a client question tool or ordinary conversation just because it is easier or already available. Pass the reported socket and window explicitly; consult the agterm skill or `agtermctl pick open --help` for syntax. Supply every option, allow a custom answer when appropriate, and wait for the actual result. If the picker fails because of a sandbox restriction or a likely sandbox-related socket access error, retry the same picker using the shell tool's elevated-permission request, with a clear justification, before falling back. Follow the client permission policy; do not bypass restrictions or retry after approval is denied. Use the next method only if the picker is unavailable, escalation is unavailable or denied, or the picker fails after the applicable retry. A cancellation is not a choice; do not treat it as an answer. Do not target an unrelated window.
2. Use a user-input form supported by the current client and mode that can represent the question and all its choices. Prefer blocking input; if asynchronous, wait for the actual answer, not merely the tool's return.
3. Ask in ordinary conversation, presenting numbered choices where applicable, and end the turn to wait for an answer.

Do not switch to Plan mode just to ask questions.

Reuse decisions and authorization already supplied; ask only about unresolved choices.

## Activation Triggers

**Explicit:**
- "ask opencode", "check with opencode", "opencode review"
- "what does opencode think", "get opencode opinion"
- "consult opencode", "run opencode on this"

**Automatic (last resort — stuck detection):**
- 4+ failed attempts at the same bug fix or investigation
- completely out of ideas, all reasonable approaches exhausted
- going in circles with no progress despite multiple different strategies

## Workflow

### Step 1: Check Availability

Resolve the real filesystem path of this `SKILL.md` (following symlinks), then the plugin root two directories above its directory. Use absolute, quoted helper paths and run from the active project/worktree root.

Read [../../references/opencode.md](../../references/opencode.md) for the existing provider/model configuration and execution/result handling. Check that `opencode` (or the configured executable) is installed. If not found, inform the user and stop. Do not substitute another provider or model.

### Step 2: Build Context

Gather context from the current conversation:

1. **What's the problem/question** — summarize in 2-3 sentences
2. **What we know** — relevant files, error messages, behavior observed
3. **What we tried** — approaches attempted and why they failed (if applicable)
4. **Specific question** — what exactly opencode should analyze or answer

OpenCode runs in a separate process and does not receive this conversation. To give it the same project context Codex follows, prepend the guidance-load preamble described in Step 3.

### Step 3: Construct Prompt

Build a focused prompt. Do NOT dump entire files — opencode has full project access and can read them itself. Provide file paths and line references so opencode knows where to look.

**Prepend a guidance-load preamble.** Identify the applicable `AGENTS.md`, `AGENTS.override.md`, and any project/user guidance Codex follows. List those files explicitly so OpenCode receives the same conventions:

```
First read these project guidance files if present: <absolute paths to the applicable guidance files>
```

- Resolve paths to literal **absolute** paths; do not leave `$HOME` or other shell variables in the prompt.
- No `@` prefix — include file paths in the prompt, not Claude Code import syntax.
- For guidance or context outside the project, use the helper's repeatable `--attach <context-file>` option to supply a snapshot.

**Template for investigation/debug:**

```
# [Investigation/Debug] Request

## Problem
[2-3 sentence description]

## Context
- Files: [path/to/file.go:lineNumber, ...]
- Observed: [what's happening]
- Expected: [what should happen]

## What We Tried
[List approaches and outcomes, or "First consultation" if fresh question]

## Question
[Specific, focused question for opencode to answer]

Provide:
1. Root cause analysis (if debugging)
2. Concrete recommendation with file:line references
3. Why previous approaches failed (if applicable)

Keep response focused and actionable.
```

**Template for code review (adversarial):**

When asked for a code review, use the original adversarial prompt in [../../references/review-contract.md](../../references/review-contract.md). It requires structured JSON output. The helper appends this prompt automatically in review mode, so supply the scope, focus, and context in the request without duplicating the contract.

### Step 4: Execute OpenCode

Write the resolved prompt to a UTF-8 file, preserving literal text instead of shell-interpolating it. Run the bundled helper with quoted absolute paths:

```bash
python3 "<plugin-root>/scripts/ask-opencode.py" "<prompt-file>"
```

For code review, add `--mode review`. For a full Git branch review, also add `--diff-base <base-ref>`; for a focused file review or non-Git investigation, specify the scope in the prompt. Use repeatable `--attach <context-file>` arguments when needed.

**Execution rules:**
- Use the client's supported background/yield-and-resume mechanism for a long call when available; do not assume Claude Code's `run_in_background` or `BashOutput` tools exist.
- Wait for the final result; do not launch a second query while the first is running.
- Be patient during reasoning; silence is not a completed answer.
- The timeout is `external_review_timeout` from the shared configuration (default: 600 seconds). Provider and model also come from that configuration.
- OpenCode's consultation process has reading/search tools, with edits, shell commands, questions, and delegation disabled. If execution is needed, run the authorized diagnostic in Codex and supply its output.
- The helper returns a JSON envelope: `completed` with `text` for advice, `reviewed` with `review` for structured review, or `skipped`/`failed` with details. Report an unavailable tool, invalid output, or timeout as such rather than as a clean review.

### Step 5: Present Results

1. **Extract opencode's analysis** — skip session info, token counts, prompt echo
2. **Parse structured output** — for reviews, opencode returns JSON; parse and present as structured findings
3. **Add your assessment** — agree, disagree, or note caveats
4. **STOP and ask** — do NOT apply any fixes or changes without explicit user approval, unless the current task already authorizes those fixes

**For investigation/debug responses** (unstructured):

```
**OpenCode Analysis:**

[OpenCode's response — cleaned up and formatted]

---

**Assessment:** [Your 2-3 sentence evaluation]

**Proposed action:** [What opencode suggests — awaiting approval]
```

**For review responses** (structured JSON):

Parse the JSON output and present findings sorted by severity, filtered by confidence:

```
**OpenCode Review: [verdict]**
[summary]

**Findings** (N issues):

1. **[critical]** title (confidence: 0.9)
   file.go:42-55
   [body]
   → [recommendation]

2. **[high]** title (confidence: 0.8)
   ...

**Next steps:** [list]

---

**Assessment:** [Your evaluation — which findings are valid, which are false positives]
```

- skip findings with confidence < 0.3 (likely noise)
- group by severity: critical → high → medium → low
- if verdict is "approve" and no findings, just say "opencode found no material issues"

**CRITICAL: After presenting findings, STOP and ask the user what to do next unless the current task already authorizes implementation of those fixes. OpenCode findings are input for discussion, not automatic work orders.**

## Important Rules

- **Read-only always** — OpenCode analyzes, Codex implements. Never let OpenCode edit files.
- **Don't duplicate files** — opencode has full project access. Provide paths, not content.
- **Focused prompts** — specific questions get better answers than broad "review everything".
- **Background execution** — use the client's supported background/yield mechanism when available to avoid shell-call time limits.
- **One question at a time** — if multiple concerns, run separate opencode queries.
- **Critical thinking** — opencode can be wrong. Evaluate its suggestions before implementing.

## When NOT to Use

- Simple questions you already know the answer to
- Tasks where the solution is clear and just needs implementation
- File searches or codebase navigation (use Grep/Glob instead)

## Troubleshooting

- **OpenCode not found**: check `opencode` or the configured executable and install OpenCode if needed.
- **Authentication**: configure credentials for the selected provider in OpenCode.
- **Timeout**: increase `external_review_timeout` in the shared configuration for complex analyses.
- **Off-target response**: refine the prompt with more specific file:line references.
- **Invalid or empty output**: inspect the helper's error; do not treat it as a clean review or silently switch provider/model.
