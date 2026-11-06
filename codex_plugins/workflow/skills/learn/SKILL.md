---
name: learn
description: Update project AGENTS.md with strategic knowledge discovered during this session — or an established personal/local notes destination for per-developer/per-checkout discoveries. Defers to any project- or user-defined memory-placement guidance instead of overriding it. Use when user says "learn", "save knowledge", "update AGENTS.md", "capture learnings", or at end of significant work sessions.
---

# Learn

Review the current conversation history and identify strategic, reusable project knowledge that should be captured in the project AGENTS.md file. Route genuinely personal or environment-specific discoveries to an established personal/local notes destination when one exists.

## Questions in Codex

Ask one question at a time and wait for the user's answer before continuing with any step that depends on it. Respect higher-priority client instructions and use the first suitable method below:

Before selecting a question method, run `sh <skill-directory>/scripts/question-environment.sh` (resolve `<skill-directory>` to the directory containing this SKILL.md). Read its JSON output. The script cannot detect client-provided tools: check the tools actually exposed in the current client and mode. Use the reported environment IDs to address the current session and window. A failed connection is specific to the execution context; do not bypass its restrictions.

1. **For every single-choice question, use `agtermctl pick` first when the script reports a candidate.** This is required, not merely a preference: do not choose a client question tool or ordinary conversation just because it is easier or already available. Pass the reported socket and window explicitly; consult the agterm skill or `agtermctl pick open --help` for syntax. Supply every option, allow a custom answer when appropriate, and wait for the actual result. If the picker fails because of a sandbox restriction or a likely sandbox-related socket access error, retry the same picker using the shell tool's elevated-permission request, with a clear justification, before falling back. Follow the client permission policy; do not bypass restrictions or retry after approval is denied. Use the next method only if the picker is unavailable, escalation is unavailable or denied, or the picker fails after the applicable retry. A cancellation is not a choice; do not treat it as an answer. Do not target an unrelated window.
2. Use a user-input form supported by the current client and mode that can represent the question and all its choices. Prefer blocking input; if asynchronous, wait for the actual answer, not merely the tool's return.
3. Ask in ordinary conversation, presenting numbered choices where applicable, and end the turn to wait for an answer.

Do not switch to Plan mode just to ask questions.

Reuse decisions and authorization already supplied; ask only about unresolved choices.

## Analysis Process

1. **Review Session History**
   - Examine all files read and modified during this session
   - Identify patterns discovered while working on tasks
   - Note architectural insights gained from exploring the codebase

2. **Extract Strategic Knowledge**
   - Filter out tactical details (bug fixes, specific implementations)
   - Focus on reusable patterns and project structure
   - Identify conventions and architectural decisions

3. **Categorize Findings**
   - Project architecture and structure
   - Data flow patterns
   - External service integrations
   - Project-specific conventions
   - Key dependencies and their purposes
   - Configuration patterns
   - Testing strategies
   - Build and deployment processes
   - Operational knowledge (debugging, DevOps)

## Destinations

This skill uses the project's Codex instruction-discovery and memory-placement conventions:

- **`AGENTS.md`** (project guidance, team-shared) — the default destination for architecture, conventions, integration patterns, and knowledge useful to the whole team. Read applicable guidance first. If a non-empty `AGENTS.override.md` is active at the destination, identify the active file and use the project's placement rules instead of silently editing an inactive `AGENTS.md`.
- **Established personal/local notes** — used only when a destination already exists and the discovery describes per-developer/per-checkout state meaningful only on this machine. Verify the destination's tracking/ignore state before treating it as private. If no destination is established, ask where to save the personal discovery or present it without saving. Do not invent `AGENTS.local.md` or use `AGENTS.override.md` as an automatic personal-memory substitute: an override replaces the same-directory base guidance rather than supplementing it.

**Counter-example:** *"We keep credentials in `~/.aws/credentials`"* mentions a user-home path but describes a team-wide convention. Such notes belong in project guidance, without credential values. Never capture secrets.

Read applicable global guidance under `${CODEX_HOME:-$HOME/.codex}` to avoid duplicating cross-project knowledge. This skill never writes global guidance.

**Default for ambiguous non-personal cases: project AGENTS.md.** Defer to documented project- or user-level memory-placement guidance.

## What Qualifies

**INCLUDE** - Strategic discoveries from this session:
- Architectural patterns uncovered while working
- Project structure insights gained from navigation
- Conventions noticed across multiple files
- Integration patterns discovered
- Configuration approaches identified
- Testing strategies observed
- Build/deployment processes encountered
- Performance optimizations found
- Security implementations discovered
- Operational knowledge:
  - Database locations and connection details per environment
  - Useful queries discovered during debugging
  - Testing procedures and verification steps
  - Deployment workflows and commands
  - Log locations and monitoring endpoints
  - Environment-specific quirks and gotchas

**EXCLUDE** - Session-specific tactical work:
- The specific bug we fixed
- The particular feature we implemented
- Temporary workarounds we used
- One-off code changes
- TODO items we encountered
- Historical context about changes

## Decision Criteria

Ask yourself for each discovery:
- "Will this help understand the project in 6 months?"
- "Is this a pattern that appears multiple times?"
- "Does this represent a project-wide convention?"
- "Would knowing this speed up future development?"
- "Would this save debugging time in the future?" (for operational knowledge)

## Workflow

### 1. Check for Existing Memory-Placement Guidance
Before applying the routing rules below, read applicable project `AGENTS.md` / `AGENTS.override.md` files, any referenced placement instructions, and applicable global guidance under `${CODEX_HOME:-$HOME/.codex}`. If documented memory-placement guidance exists — for example, a placement decision tree, a project-specific triage workflow, or specific destinations — defer to it instead of using this skill's defaults. The remaining steps apply only when no such guidance is found. Do not assume Claude Code's `.claude/rules/` discovery applies to Codex.

### 2. Check Existing Memory Content
Read the active project guidance, established personal/local notes (if present), and applicable global Codex guidance to avoid duplication — including cross-project entries already captured in user guidance.

### 3. Early Exit if Nothing Found
If no new strategic knowledge was discovered during this session:
- Report "no new strategic knowledge to capture"
- Do NOT ask for user input
- End the skill execution

### 4. Classify Each Discovery
For each discovery, determine its destination per the [Destinations](#destinations) rules: default to active project guidance, and route to established personal/local notes only when both destination-exists and personal-content criteria are met (and the counter-example caveat does not apply).

### 5. New Knowledge to Add
Present discovered knowledge formatted for the chosen destination, tagging each block with its inferred file:
```markdown
## [Section Name] → project AGENTS.md
- Discovery 1
- Discovery 2
```

### 6. User Confirmation

**CRITICAL**: Ask for granular selection of what to save, following Questions in Codex above. If the user already selected exactly what to save and where, carry out that selection without asking again.

Build options dynamically based on discoveries:
- First option: "All knowledge" - save everything to its inferred destination
- Last option before custom: "None" - skip saving entirely
- Middle options: Individual knowledge items (up to 2-3 most significant), each labelled with its inferred destination
- User can always type custom selection via "Other"

Example with 3 discoveries (2 project, 1 personal):
```yaml
question: "Which knowledge should I save?"
options:
  - label: "All (3 items)"
    description: "Save all discovered patterns to their inferred destinations"
  - label: "Service discovery pattern → project AGENTS.md"
    description: "Project-wide convention for how modules find each other"
  - label: "Local toolchain variant → personal notes"
    description: "Per-checkout build runner override (only relevant on this machine)"
  - label: "None"
    description: "Skip saving, nothing worth keeping"
```

Example with 1 discovery:
```yaml
question: "Save this knowledge?"
options:
  - label: "Yes → project AGENTS.md"
    description: "Save: [brief description of the discovery]"
  - label: "No"
    description: "Skip saving"
```

After user selection:
- "All" -> save everything to its inferred destination
- "None" -> end without saving
- Specific item -> save only that item, to the inferred destination shown in the label
- "Other" -> user types custom selection of **which discoveries** to save (comma-separated item names). Destinations follow the labels shown — `"Other"` does NOT redirect a destination to an arbitrary path. To override a routing decision, the user should decline the auto-classification, edit the destination file manually, or re-invoke the skill with explicit instructions.

## Important Guidelines
- Only capture genuinely new discoveries from this session
- Don't duplicate existing project AGENTS.md, personal notes, or global Codex guidance
- Focus on patterns observed, not specific code written
- Keep descriptions concise and actionable
- Follow Questions in Codex for confirmation. If a widget cannot represent every discovery, split the selection across successive questions or numbered conversation; do not drop findings to fit its limits
- If no knowledge found, exit early without asking
- **Defer to project- or user-level memory-placement guidance discovered in step 1** — do not override existing conventions with this skill's defaults
