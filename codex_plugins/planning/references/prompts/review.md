# Review fanout playbook

This file is a playbook for the main orchestrator session — NOT a prompt to spawn into a subagent. Use the available Codex subagent interface; the main session initiates fanout and leaf reviewers do not delegate further.

Resolve placeholders (`DEFAULT_BRANCH`, `PLAN_FILE_PATH`, `PROGRESS_FILE_PATH`, `REVIEW_PHASE`, `RESOLVE_SCRIPT`, `WORKING_DIRECTORY`), then follow the instructions below from the main session: launch the specified parallel Agent calls, collect findings from all returned agents, and pass them to the fixer subagent. The orchestrator does NOT fix issues itself — the fixer is a separate subagent that handles fixes.

## Subagent Model

Use the orchestrator's resolved `SUBAGENT_MODEL` launch setting from `planning-exec`. On each reviewer launch, pass the selected model as the native tool's `model` argument when non-empty; otherwise omit `model`. Use a fresh context when required for overrides (`fork_turns: "none"` with `spawn_agent`), supplying the complete reviewer prompt and working context. Do not replace `SUBAGENT_MODEL` as text in this playbook. If model selection is unsupported or rejected, report it without silently substituting another model.

## How to fan out (READ THIS CAREFULLY)

Launch the N specialists using available, authorized Codex subagent tools. Start all reviewers in a concurrency-sized batch before waiting, then launch any remaining batch. Wait for all readers before a fixer writes. If delegation is unavailable and no model override is configured, perform the same checks sequentially in the parent and report the lack of independent contexts. If a model override is configured, follow the executor's Subagent Model rules instead of silently using the parent.

Each agent prompt MUST include: "CRITICAL: You are a READ-ONLY reviewer. Do NOT run git stash, git checkout, git reset, or any command that modifies the working tree. Other agents run in parallel. Only use read-only VCS inspection and file-reading/search tools. Run all commands in WORKING_DIRECTORY."

Each agent prompt MUST require severity tagging on every finding. Tag categories:
- CRITICAL: bugs causing crashes, data loss, security holes, race conditions
- MAJOR: real correctness issues — incorrect behavior, missing error handling, broken contracts
- MINOR: style, doc drift, doc/code inconsistencies, nits, optional improvements

Agents must format each finding on its own line as: `SEVERITY: file:line — description`. Findings without an explicit severity prefix are treated as MINOR.

Do NOT embed diffs in agent prompts — tell each agent to run git commands itself. Embedding large diffs slows parallel launch and inflates context.

## Comprehensive mode (5 agents)

Used when `REVIEW_PHASE` is `comprehensive`.

Resolve each agent's prompt file using the resolve script (these are bash invocations, not parallel work — run them first, then assemble the agent prompts):

```
bash RESOLVE_SCRIPT agents/quality.txt
bash RESOLVE_SCRIPT agents/implementation.txt
bash RESOLVE_SCRIPT agents/testing.txt
bash RESOLVE_SCRIPT agents/simplification.txt
bash RESOLVE_SCRIPT agents/documentation.txt
```

For each resolved agent prompt, replace `DEFAULT_BRANCH` with the actual value, then prepend:

"CRITICAL: You are a READ-ONLY reviewer. Do NOT run git stash, git checkout, git reset, or any command that modifies the working tree. Other agents run in parallel. Only use read-only VCS inspection and file-reading/search tools. Run all commands in WORKING_DIRECTORY.

Run `DIFF_COMMAND` to see all changes. Read the actual source files for full context — do not review from diff alone.

The plan file at PLAN_FILE_PATH describes the goal and requirements — use it to understand what the code is supposed to do.

Read the progress file at PROGRESS_FILE_PATH for context on previous review iterations and fixes. Re-evaluate all findings independently — previous fixes may be incomplete or wrong, and previously dismissed issues may be real.

Tag every finding with severity (CRITICAL/MAJOR/MINOR) and format each on its own line as: `SEVERITY: file:line — description`."

Launch the 5 specialists (quality, implementation, testing, simplification, documentation) with the assembled prompts, in batches that fit the client's available concurrency, applying Subagent Model on every launch.

After ALL 5 agents return, produce a STRICT bullet-list report — no prose summary, no narrative, no "agents converge on" sentences. Format requirements:

- Group findings by severity in this order: CRITICAL, MAJOR, MINOR. Use a heading per severity (`### CRITICAL`, `### MAJOR`, `### MINOR`). Skip a severity heading if it has zero findings.
- Under each heading, one bullet per finding using EXACTLY this shape: `- <agent-name>: <file:line> — <description>`
- Preserve the original agent attribution (e.g. `quality`, `implementation`, `testing`, `simplification`, `documentation` — whichever agent files were resolved). Do NOT rewrite as "agents" or "multiple agents".
- If two agents reported the same file:line + same issue, merge into one bullet and prefix both agent names separated by `+` (e.g. `- quality+implementation: main.go:12 — ...`).
- Do NOT verify, fix, or dismiss findings here — the fixer agent does that. Just emit the report verbatim from agent outputs.
- Omit agents that found nothing entirely (no need to mention them).
- After the bullet list, on its own line, emit one summary line: `Total: <N> findings (<C> critical, <M> major, <m> minor)`.

Do NOT add explanatory prose, recommendations, or commentary. The list goes straight to the fixer.

## Critical-only mode (2 agents)

Used when `REVIEW_PHASE` is `critical`.

Resolve only `quality.txt` and `implementation.txt` using the resolve script. Replace `DEFAULT_BRANCH` in each, then prepend the same READ-ONLY preamble as comprehensive mode, plus:

"Report ONLY critical and major issues — bugs, security vulnerabilities, data loss risks, broken functionality, incorrect logic, missing critical error handling. Ignore style, minor improvements, suggestions. Tag every reported finding with severity (CRITICAL or MAJOR) and format each on its own line as: `SEVERITY: file:line — description`."

Launch the 2 specialists using the same available, authorized Codex subagent interface and Subagent Model handling as comprehensive mode.

After BOTH agents return, produce the same STRICT bullet-list report as comprehensive mode (groupings by severity, exact bullet shape, agent attribution preserved, no prose summary). Additional rule for this mode:

- Drop any MINOR findings if agents returned them anyway. Only CRITICAL and MAJOR headings appear here.
- If neither agent reported CRITICAL or MAJOR findings, emit exactly: `Critical re-check: clean — no critical/major findings.` and stop.
