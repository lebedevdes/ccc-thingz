---
name: brainstorm
description: Use before any creative work or significant changes. Activates on "brainstorm", "let's brainstorm", "deep analysis", "analyze this feature", "think through", "help me design", "explore options for", or when user asks for thorough analysis of changes, features, or architectural decisions. Guides collaborative dialogue to turn ideas into designs through one-at-a-time questions, approach exploration, and incremental validation.
---

# Brainstorm

Turn ideas into designs through collaborative dialogue before implementation.

## custom rules loading

before starting, run the bundled `scripts/resolve-rules.sh` with `brainstorm-rules.md` as its argument using the available shell tool. resolve the script's absolute path relative to the directory containing this `SKILL.md`; keep the working directory at the user's project root so project rules resolve correctly. quote paths, including paths containing spaces. do not assume the plugin is installed in its source checkout.

if the output is non-empty, treat it as additional instructions that supplement (not replace) the built-in rules below. apply custom rules alongside the skill's own instructions throughout the brainstorm process — they may influence design preferences, naming conventions, technology choices, or other aspects of the brainstorm session. custom rules content is guidance for the brainstorm dialogue, not content to embed verbatim in the output.

### rules management

when the user asks to add, show, or clear custom brainstorm rules, handle these operations:

- **show rules**: run the bundled `scripts/resolve-rules.sh` with `brainstorm-rules.md` as above and display the output. if the output is empty, tell the user no custom rules are configured at either level. otherwise, to determine the source, check if `.codex/brainstorm-rules.md` exists and is non-empty (project-level) — if not, the output came from user-level. tell the user which level it came from.
- **add/update project rules**: write content to `.codex/brainstorm-rules.md` in the current working directory.
- **add/update user rules**: resolve `${CODEX_HOME:-$HOME/.codex}` and write content to `brainstorm-rules.md` there. respect the client's filesystem permissions; if writing there is unavailable, explain the limitation and offer project-level instead.
- **clear project rules**: delete `.codex/brainstorm-rules.md`.
- **clear user rules**: delete `${CODEX_HOME:-$HOME/.codex}/brainstorm-rules.md`, respecting the client's filesystem permissions.

project-level rules (`.codex/brainstorm-rules.md`) take precedence over user-level rules (`${CODEX_HOME:-$HOME/.codex}/brainstorm-rules.md`). when both non-empty files exist, only project-level rules are loaded. empty files are treated as absent and fall through to the next level. see [references/custom-rules.md](references/custom-rules.md) for full documentation on the rules mechanism.

**CRITICAL: this skill must NEVER modify its own files (skills, scripts, references, hooks, plugin.json). the ONLY files it may create or modify for rules management are `.codex/brainstorm-rules.md` and `${CODEX_HOME:-$HOME/.codex}/brainstorm-rules.md`. if the user asks to change the skill's behavior, suggest creating a plan — do not edit skill files directly.**

## Questions in Codex

Ask one question at a time and wait for the user's answer before continuing with any step that depends on it. Respect higher-priority client instructions and use the first suitable method below:

Before selecting a question method, run `sh <skill-directory>/scripts/question-environment.sh` (resolve `<skill-directory>` to the directory containing this SKILL.md). Read its JSON output. The script cannot detect client-provided tools: check the tools actually exposed in the current client and mode. Use the reported environment IDs to address the current session and window. A failed connection is specific to the execution context; do not bypass its restrictions.

1. **For every single-choice question, use `agtermctl pick` first when the script reports a candidate.** This is required, not merely a preference: do not choose a client question tool or ordinary conversation just because it is easier or already available. Pass the reported socket and window explicitly; consult the agterm skill or `agtermctl pick open --help` for syntax. Supply every option, allow a custom answer when appropriate, and wait for the actual result. If the picker fails because of a sandbox restriction or a likely sandbox-related socket access error, retry the same picker using the shell tool's elevated-permission request, with a clear justification, before falling back. Follow the client permission policy; do not bypass restrictions or retry after approval is denied. Use the next method only if the picker is unavailable, escalation is unavailable or denied, or the picker fails after the applicable retry. A cancellation is not a choice; do not treat it as an answer. Do not target an unrelated window.
2. Use a user-input form supported by the current client and mode that can represent the question and all its choices. Prefer blocking input; if asynchronous, wait for the actual answer, not merely the tool's return.
3. Ask in ordinary conversation, presenting numbered choices where applicable, and end the turn to wait for an answer.

Do not switch to Plan mode just to ask questions. Do not assume Codex can switch its own collaboration mode.

## Process

### Phase 1: Understand the Idea

Check project context first, then ask questions one at a time:

1. **Gather context** - check files, docs, recent commits relevant to the idea
2. **Ask questions one at a time** - prefer multiple choice when possible
3. **Focus on**: purpose, constraints, success criteria, integration points

Do not overwhelm with multiple questions. One question per message. If a topic needs more exploration, break it into multiple questions.

### Phase 2: Explore Approaches

Once the problem is understood:

1. **Propose 2-3 different approaches** with trade-offs
2. **Lead with recommended option** and explain reasoning
3. **Present conversationally** - not a formal document yet

Example format:
```
I see three approaches:

**Option A: [name]** (recommended)
- how it works: ...
- pros: ...
- cons: ...

**Option B: [name]**
- how it works: ...
- pros: ...
- cons: ...

Which direction appeals to you?
```

### Phase 3: Present Design

After approach is selected:

1. **Break design into sections** of 200-300 words each
2. **Ask after each section** whether it looks right
3. **Cover**: architecture, components, data flow, error handling, testing
4. **Be ready to backtrack** if something doesn't make sense

Do not present entire design at once. Incremental validation catches misunderstandings early.

### Phase 4: Next Steps

After design is validated, ask "Design looks complete. What's next?" following Questions in Codex above, unless the user has already specified the next step. Offer these options:

- **Write plan**: create `docs/plans/yyyymmdd-<task-name>.md` with implementation steps via `$planning-make` if installed; otherwise write the plan directly. Pass brainstorm context (discovered files, selected approach, design decisions) so planning has full context without re-asking questions
- **Plan mode**: explain how the user can switch to Plan mode for detailed planning if the client supports it; otherwise offer to write the plan in the current conversation
- **Start now**: proceeds directly if design is simple enough

## Key Principles

- **One question at a time** - do not overwhelm with multiple questions
- **Multiple choice preferred** - easier to answer than open-ended when possible
- **YAGNI ruthlessly** - remove unnecessary features from all designs, keep scope minimal
- **Explore alternatives** - always propose 2-3 approaches before settling
- **Incremental validation** - present design in sections, validate each
- **Be flexible** - go back and clarify when something doesn't make sense
- **Lead with recommendation** - have an opinion, explain why, but let user decide
- **Duplication vs abstraction** - when code repeats, ask user: prefer duplication (simpler, no coupling) or abstraction (DRY but adds complexity)? explain trade-offs before deciding

## Task Tracking

When implementing after brainstorm:
- Track implementation tasks using available task management tools (task lists, plan file checkboxes, or similar)
- Mark each task as completed immediately when done (do not batch)
- Keep user informed of progress through status updates
