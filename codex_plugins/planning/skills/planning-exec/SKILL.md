---
name: planning-exec
description: "Execute plan tasks sequentially using subagents. Use when user says 'exec', 'execute plan', 'run plan', or wants to implement a plan file task by task with isolated subagents."
---

# planning-exec

Execute plan file tasks sequentially, each in an isolated subagent.

## Arguments

- the user's skill arguments — path to plan file (optional; if omitted, ask user to pick from `plans_dir` directory from the loaded configuration, default: `docs/plans/`)

## Codex Setup

Resolve the real filesystem path of this `SKILL.md` (following symlinks), then the plugin root two directories above its directory. In the examples below, replace `PLUGIN_ROOT` with that absolute path; it is a prompt placeholder, not an automatically provided environment variable. Quote filesystem paths in shell calls. Run shell calls and subagents from the active project/worktree root; a directory change in one call does not persist into later calls.

Run `python3 PLUGIN_ROOT/scripts/planning_config.py` to load settings. These settings replace Claude Code's `userConfig`. For configuration or customization requests, read [../../references/configuration.md](../../references/configuration.md) and handle only the requested operation. Do not change bundled skill files to store preferences.

## Questions in Codex

Ask one question at a time and wait for the user's answer before continuing with any step that depends on it. Respect higher-priority client instructions and use the first suitable method below:

Before selecting a question method, run `sh <skill-directory>/scripts/question-environment.sh` (resolve `<skill-directory>` to the directory containing this SKILL.md). Read its JSON output. The script cannot detect client-provided tools: check the tools actually exposed in the current client and mode. Use the reported environment IDs to address the current session and window. A failed connection is specific to the execution context; do not bypass its restrictions.

1. **For every single-choice question, use `agtermctl pick` first when the script reports a candidate.** This is required, not merely a preference: do not choose a client question tool or ordinary conversation just because it is easier or already available. Pass the reported socket and window explicitly; consult the agterm skill or `agtermctl pick open --help` for syntax. Supply every option, allow a custom answer when appropriate, and wait for the actual result. If the picker fails because of a sandbox restriction or a likely sandbox-related socket access error, retry the same picker using the shell tool's elevated-permission request, with a clear justification, before falling back. Follow the client permission policy; do not bypass restrictions or retry after approval is denied. Use the next method only if the picker is unavailable, escalation is unavailable or denied, or the picker fails after the applicable retry. A cancellation is not a choice; do not treat it as an answer. Do not target an unrelated window.
2. Use a user-input form supported by the current client and mode that can represent the question and all its choices. Prefer blocking input; if asynchronous, wait for the actual answer, not merely the tool's return.
3. Ask in ordinary conversation, presenting numbered choices where applicable, and end the turn to wait for an answer.

Do not switch to Plan mode just to ask questions.

Reuse decisions and authorization already supplied; ask only about unresolved choices. Do not assume Codex can switch its own collaboration mode.

## Codex Delegation

Use available, authorized Codex subagent tools, with a fresh task context where supported. Pass each worker the absolute working directory, plan/progress paths, plugin root, settings, custom rules, and resolved prompt. Do not assume Claude Code's `Agent`, `Task`, `subagent_type`, `bypassPermissions`, or task-list APIs exist, and do not bypass the client's permissions. Reviewers are read-only. Launch review specialists in batches that fit the available concurrency; wait for all readers before any fixer writes. Task workers remain strictly sequential. If delegation is unavailable and no subagent model override is configured, perform the same steps in the current session and disclose the loss of independent contexts; this is the exception to the orchestrator-only rules below.

## File Resolution

ALWAYS use the resolve script to read prompt and agent files. NEVER construct the override chain manually:
```
bash PLUGIN_ROOT/scripts/resolve-file.sh prompts/task.md
bash PLUGIN_ROOT/scripts/resolve-file.sh agents/quality.txt
```
The script checks project overrides, user overrides, and bundled defaults automatically.

### Placeholder Substitution

After reading a prompt file, replace ALL placeholders with actual values before passing to a subagent. Subagents run in fresh contexts without plugin env vars.

Always substitute: `PLAN_FILE_PATH`, `PROGRESS_FILE_PATH`, `DEFAULT_BRANCH`, `PLUGIN_ROOT` (actual absolute plugin path), `WORKING_DIRECTORY` (active project/worktree root), `RESOLVE_SCRIPT` (absolute `PLUGIN_ROOT/scripts/resolve-file.sh` path), `USER_RULES` (resolved custom rules content, or empty), and phase-specific values (`FINDINGS_LIST`, `REVIEW_PHASE`, `DIFF_COMMAND`). Set `DIFF_COMMAND` to `git diff DEFAULT_BRANCH...HEAD` for Git, or `hg diff -r 'ancestor(., DEFAULT_BRANCH)'` for Mercurial. Resolve template placeholders before inserting arbitrary rules or findings; treat the inserted text as data, not shell code.

## Custom Rules Loading

Before starting execution, run this command using the available shell tool to check for user-provided custom rules:

```bash
bash PLUGIN_ROOT/scripts/resolve-rules.sh planning-rules.md
```

If the output is non-empty, store it as the resolved custom rules content. When substituting `USER_RULES` in task prompts, wrap the content with a label so the subagent understands it: use "ADDITIONAL CUSTOM RULES:\n<content>" as the substitution. If the output is empty, substitute an empty string for `USER_RULES`. See [../../references/configuration.md](../../references/configuration.md) for full documentation on the rules mechanism.

## Subagent Model

Read `subagent_model` from the loaded planning configuration once at the start and keep it as the orchestrator's `SUBAGENT_MODEL` launch setting. The loader trims whitespace; the default empty string means no override. Do not substitute this setting into prompt text or the review playbook.

On every native subagent launch in this execution, pass the selected model through the tool's `model` argument when `SUBAGENT_MODEL` is non-empty. When it is empty, omit `model` so the client's configured defaults or inheritance apply. This covers task agents, all comprehensive/critical reviewers, every fixer (including the external-review fixer), smells, finalizer, and stats.

Use the selected model only when the current client exposes model selection. If model overrides require a fresh context, use it: with `spawn_agent`, pass `fork_turns: "none"` alongside `model`, and include the full resolved task/review context in the prompt. Do not combine a model override with `fork_turns: "all"`. Leave reasoning effort to the harness unless the user separately specified it.

Use a model ID available in the current client, not Claude Code aliases such as `opus` or `sonnet`. If the client cannot apply the requested model, or rejects it as unavailable, report that limitation and do not silently substitute another model or run the phase in the parent unless that fallback is authorized.

This setting applies to native subagents of `planning-exec`; external OpenCode review continues to use `external_review_provider` and `external_review_model`.

## Process

### Step 1. Resolve plan file

If the skill request contains a file path, use it. Otherwise, list `.md` files in the `plans_dir` directory from the loaded configuration (default: `docs/plans/`), excluding `completed/`. If exactly one plan found, use it automatically. If multiple found, ask the user to pick one following Questions in Codex.

Read the plan file. Count total Task sections (`### Task N:` or `### Iteration N:`) to know the scope.

Determine the default branch: `bash PLUGIN_ROOT/scripts/detect-branch.sh`

Note: in `hg` repos, detect-branch.sh returns `remote/<name>` (checking `master`, `main`, `trunk` in that order) in modern-Mercurial repos that expose upstream default via `remote/<name>` refs, and falls back to `default` in repos that use the traditional named-branch convention instead. The external-review prompt (`prompts/external-review.md`) and the finalize prompt (`prompts/finalizer.md`) use git-specific commands and are not VCS-translated upstream. Both phases will be skipped (see step 9 and step 11, which re-detect VCS locally). Users who want hg-native review/finalize can override via `.codex/exec-plan/prompts/external-review.md` and `.codex/exec-plan/prompts/finalizer.md` — any `git rebase origin/DEFAULT_BRANCH` in the bundled template must be replaced with the hg equivalent in the override, e.g. `hg rebase -d remote/master` when the repo exposes remote-tracking refs, or `hg rebase -d default` when it uses the traditional named-branch convention.

### Step 2. Ask about worktree isolation

**hg skip**: Detect VCS with `bash PLUGIN_ROOT/scripts/detect-vcs.sh`. If VCS is `hg`, skip the worktree question and proceed in the current directory. Git worktrees have no direct hg equivalent here; users wanting hg isolation can prepare `hg share` before invoking `$planning-exec`.

First detect current branch state — run `git branch --show-current` and compare with the default branch detected earlier. Two cases:

**Case A — currently on the default branch (master/main/trunk).** Step 4 will create a new feature branch. Ask "Where should the feature branch be created?":
- **Worktree (isolated)** — create the feature branch in a new isolated Git worktree; the main working directory stays on the default branch.
- **In-place** — create the feature branch in this working directory; it switches to the feature branch for the run.

**Case B — currently on a feature branch.** Ask "You're already on a feature branch. Run the plan here, or in an isolated worktree?":
- **Stay here** — run the plan in this working directory on the existing branch.
- **Move to worktree** — fork the current HEAD into a new branch in an isolated worktree; the main directory stays untouched.

In BOTH cases, follow Questions in Codex and wait for the choice unless the user already specified it. Auto mode does not settle an unresolved isolation choice.

**If the user picks Worktree or Move to worktree** — set `worktree_mode = true` and follow [../../references/worktrees.md](../../references/worktrees.md). The main working directory MUST NOT be touched: derive the feature name without side effects, create the worktree directly with native client support or `git worktree add`, carry the selected plan/settings into it, and pass its absolute root to every later operation. Verify the original checkout stayed untouched. **Skip Step 4** because the branch already exists in the worktree. Report the worktree path and branch at completion.

**If the user picks In-place or Stay here** — set `worktree_mode = false` and proceed normally; Step 4 creates or keeps the branch in this directory.

### Step 3. Create task list

Create a task list using an available planning/task tool or a checklist before starting work. Create one item for each plan Task section, with its title and checkbox items, then add:

- Review phase 1: comprehensive — 5 review specialists + fixer
- Review phase 2: code smells — smells agent + fixer
- Review phase 3: external — adversarial OpenCode review loop
- Review phase 4: critical only — 2 review specialists + fixer
- Finalize — rebase, clean up commits, verify
- Stats summary — available session metrics + VCS statistics

Mark each task in progress when starting and completed immediately when done.

### Step 4. Create branch

**Skip this step entirely when `worktree_mode` is true** — Step 2 already created the branch (`<name>`) inside the isolated worktree, and running this here would `git checkout -b` in the main working tree and break isolation. Carry `<name>` forward as the branch name and go to Step 5.

Otherwise (in-place mode), **MANDATORY**: run the script below. Do NOT create the branch manually — the script strips the date prefix from the plan filename (e.g., `20260329-feature-name.md` → branch `feature-name`).

```
bash PLUGIN_ROOT/scripts/create-branch.sh <plan-file-path>
```

The script creates a feature branch if currently on main/master, or stays on the current branch if already on a feature branch. Capture and use the branch name it outputs.

### Step 5. Initialize progress file

Initialize the progress file: `bash PLUGIN_ROOT/scripts/init-progress.sh /tmp/progress-<plan-name>.txt <plan-file-path> <branch-name>` (derive `<plan-name>` from the plan file stem, e.g., `fix-issues.md` → `progress-fix-issues`). The script creates the file with a header. Report the full progress file path to the user.

IMPORTANT: Always use `PLUGIN_ROOT/scripts/append-progress.sh` to write to the progress file after initialization. Never write directly.

### Step 6. Task loop

Repeat until no executable `[ ]` checkboxes remain in any Task section. Defer only a plan-relocation checkbox to Step 13; leave it unchecked until the actual move. Do not check off skipped manual/external work or failed validation; report it as incomplete.

1. **Re-read the plan file** (subagent modifies it each iteration)
2. **Find the first Task section** (`### Task N:` or `### Iteration N:`) that still has executable `[ ]` checkboxes, excluding only the deferred plan-relocation checkbox
3. **If none found** — all tasks complete, go to step 7
4. **Announce the task to the user** — before spawning the subagent, output a visible summary:
   - Task number and title (from the `### Task N:` header)
   - List all `[ ]` checkbox items in that task section
   - Example output:
     ```
     --- Task 1: Fix error handling ---
     - [ ] Handle the error from os.ReadFile
     - [ ] Either log and exit or handle gracefully
     ```
5. **Spawn one task subagent** using available, authorized Codex tools, with:
   - The absolute working directory and resolved context described in Codex Delegation
   - The model launch argument from Subagent Model (omit it when unset)
   - The task prompt from `prompts/task.md`, with all placeholders substituted as described in the Placeholder Substitution section above (including `USER_RULES`)
6. **After subagent returns**, re-read the plan file and check if that task's executable checkboxes are now `[x]`, excluding only the deferred plan-relocation checkbox
   - If yes — task succeeded, continue loop
   - If no — **retry** with a fresh subagent for the same task up to `task_retries` times (loaded configuration, default: 1). If all retries fail, stop and report failure to user
7. **Report to user**: "Task N completed" (one line). The task subagent logs details to the progress file.

CRITICAL: Spawn exactly ONE task subagent per iteration and WAIT for it to return before starting the next. NEVER batch-spawn multiple task subagents in a single message. Plan tasks are ordered and interdependent — later tasks build on the files earlier tasks create, and every task subagent edits the same plan-file checkboxes and overlapping source files, so running them in parallel corrupts the plan and the working tree. The "launch in a single message for parallel execution" instruction applies ONLY to the review phases (steps 7 and 10), never to this task loop.

CRITICAL: Do NOT stop the loop based on subagent return text. The ONLY condition to stop is: no executable `[ ]` checkboxes remain in any Task section (`### Task N:` or `### Iteration N:`), excluding only the deferred plan-relocation checkbox. Always re-read the plan file to check.

CRITICAL: You are the ORCHESTRATOR. Never read code, debug errors, investigate diagnostics, or fix issues yourself. If a subagent leaves problems (compiler errors, test failures, lint issues), retry with a fresh subagent — pass the error details in the prompt so it can fix them. All code work happens inside subagents, not in the orchestrator.

Maximum iterations safety limit: 50. If reached, stop and report to user.

### Step 7. Review phase 1 — comprehensive then critical re-check

After all tasks complete, run a comprehensive code review on iteration 1, then narrow to critical-only re-checks on subsequent iterations to verify the fixer's work without re-running the full heavy sweep.

Report to user: "--- Review phase 1: comprehensive ---"

Loop up to `review_iterations` times (loaded configuration, default: 5). Track the current iteration number:

1. **Read review.md as a playbook (NOT as a subagent prompt)** — resolve `prompts/review.md` through the override chain and read it from this main session. It tells YOU (the orchestrator) which specialist agents to fan out for the current `REVIEW_PHASE`. Substitute `DEFAULT_BRANCH`, `PLAN_FILE_PATH`, `PROGRESS_FILE_PATH`, `PLUGIN_ROOT`, and `REVIEW_PHASE` in the resolved content. Then follow the playbook FROM THIS SESSION: launch the specified Codex reviewers before waiting, in batches fitting available concurrency. The fanout is initiated by the main orchestrator; leaf workers do not delegate further.
   - **Iteration 1**: set `REVIEW_PHASE` to `comprehensive`. Per the playbook, launch 5 parallel review agents (quality, implementation, testing, simplification, documentation), applying Subagent Model to each launch.
   - **Iteration 2 and later**: set `REVIEW_PHASE` to `critical`. Per the playbook, launch 2 parallel review agents (quality, implementation) focused on critical/major issues only, applying Subagent Model to each launch. Before this iteration, report to user: "--- Review phase 1: critical re-check (iteration N) ---"

2. **Collect findings** — collect findings from ALL launched review agents. Pass the COMPLETE output (not a summary) to the fixer. Do NOT summarize, filter, or dismiss any findings. ALL findings are actionable. Report to user with a short list of findings. Log to progress file:
   `bash PLUGIN_ROOT/scripts/append-progress.sh <progress-file> "review phase 1: findings"`
   Then pipe: `echo "<findings>" | bash PLUGIN_ROOT/scripts/append-progress.sh <progress-file>`

3. **If ALL agents reported zero issues** → report "Review phase 1: clean" and proceed to the next phase.

4. **Spawn a fixer agent** — resolve `prompts/fixer.md` through the override chain. Launch with the available, authorized Codex subagent tools, applying Subagent Model. Pass the FULL unedited review output as FINDINGS_LIST — the fixer decides what's real, not you.

5. **After fixer returns** → show the "FIXES:" section to the user. Report "Review phase 1: iteration N fixes applied". Check for uncommitted changes: detect VCS with `vcs=$(bash PLUGIN_ROOT/scripts/detect-vcs.sh)`, then run `git status --porcelain` for `git` or `hg status` for `hg`. If output is non-empty, show every reported path and warn that these uncommitted changes are absent from the committed branch diff used by the next review. This is report-only: do not retry, abort, or commit leftovers because of this check. Loop back to step 1.

If `review_iterations` reached with issues still found, report "Review phase 1: max iterations reached, moving on" and continue.

### Step 8. Review phase 2 — code smells

Report to user: "--- Review phase 2: code smells analysis ---"

Run once (no loop):

1. **Spawn a smells agent** — resolve `agents/smells.txt` through the override chain. Launch one authorized Codex subagent with the resolved agent prompt, applying Subagent Model.

2. **Collect findings** — after the agent returns, report to user with a compact list of findings (one line per finding). Log findings to progress file:
   `bash PLUGIN_ROOT/scripts/append-progress.sh <progress-file> "review phase 2: findings"`
   Then pipe the findings: `echo "<findings>" | bash PLUGIN_ROOT/scripts/append-progress.sh <progress-file>`

3. **If no issues found** → report "Smells analysis: clean" and proceed to the next phase.

4. **Spawn a fixer agent** — resolve `prompts/fixer.md` through the override chain. Launch with the available, authorized Codex subagent tools, applying Subagent Model. Pass the FULL smells output as FINDINGS_LIST.

5. **After fixer returns** → report fixes to user. Check for uncommitted changes: detect VCS with `vcs=$(bash PLUGIN_ROOT/scripts/detect-vcs.sh)`, then run `git status --porcelain` for `git` or `hg status` for `hg`. If output is non-empty, show every reported path and warn that these uncommitted changes are absent from the committed branch diff used by the next review. This is report-only: do not retry, abort, or commit leftovers because of this check. Proceed to the next phase.

### Step 9. Review phase 3 — external review

**hg skip**: Detect VCS with `vcs=$(bash PLUGIN_ROOT/scripts/detect-vcs.sh)`. If `vcs` is `hg`, skip this entire step. Report to user: "hg detected — skipping external review (git-only). Override `prompts/external-review.md` via `.codex/exec-plan/` to enable hg-native review." Proceed directly to step 10.

Report to user: "--- Review phase 3: external review ---"

Adversarial loop: the external reviewer reviews the code, fixer evaluates and fixes, the reviewer re-reviews. The loop exits early once an iteration produces no `CRITICAL` or `MAJOR` findings — minor-only iterations still get fixed by the fixer, but no further round-trip happens. Subsequent phases (smells, critical-only) act as the final safety net.

All invocations go through the existing `scripts/run-external-review.py` OpenCode runner. Use the loaded provider/model and `external_review_timeout`; do not fall back to Codex or silently substitute another model. Read [../../references/external-review.md](../../references/external-review.md) for invocation and result handling.

Loop up to `external_review_iterations` times (loaded configuration, default: 10):

1. **Resolve the review prompt** — read `prompts/external-review.md` through the override chain. Substitute `PLAN_FILE_PATH`, `PROGRESS_FILE_PATH`, and `USER_RULES`. The runner attaches the full current Git change from the merge base on every iteration, including prior fixer commits and tracked working changes, along with the plan and progress snapshots.
2. **Run the external reviewer** — write the resolved prompt to `/tmp/external-review-<plan-name>.txt` with a file-writing tool, preserving literal backticks and dollar signs. Run `python3 PLUGIN_ROOT/scripts/run-external-review.py <prompt-file> --plan-file <plan-file> --progress-file <progress-file> --diff-base <default-branch>`. Use the client's background/yield-and-resume mechanism when available and wait for the final result; do not launch duplicate reviews.
3. **Check the output** — use the runner's JSON `status`. For `clean`, the final answer contains the clean marker with no tagged findings: finish this phase and proceed to Step 10. For `skipped` or `failed`, report the reason and proceed to Step 10 while retaining the uncompleted external phase in the final report. Tagged findings win over an incidental clean marker; empty or unstructured output is failure. For `findings`, continue below.
4. **Classify severity** — for `findings`, use `has_blocking`: CRITICAL or MAJOR findings keep the loop running; minor-only findings get one fixer pass.
5. **Report findings to user** — show a compact list, one line per finding. Log and pass the COMPLETE external text to the fixer, without filtering.
6. **Spawn a fixer agent** — resolve `prompts/fixer.md`, pass the external text as `FINDINGS_LIST`, and apply Subagent Model to its native launch. The fixer verifies, fixes, commits, and reports `FIXES:`.
7. **Report fixer results** — show `FIXES:`, log to progress, and report every remaining changed/staged path. Do not commit unrelated leftovers because of this check.
8. **Decide whether to loop** — if `has_blocking` is false, report "External review: only minor findings — fixes applied, stopping loop" and proceed to Step 10. Otherwise re-run the full external review.

If `external_review_iterations` is reached with critical/major issues still found, report "External review: max iterations reached, moving on" and continue to the final internal check. Retain the unresolved result in the completion report.

### Step 10. Review phase 4 — critical only

Report to user: "--- Review phase 4: critical/major only (single pass) ---"

Same structure as step 7 but with `REVIEW_PHASE` set to `critical`. Resolve `prompts/review.md` and follow its playbook FROM THIS MAIN SESSION — launch 2 Codex review agents (quality, implementation), within available concurrency and applying Subagent Model, focusing on critical/major issues only. The main orchestrator initiates fanout; leaf reviewers do not delegate further. Same fixer flow — pass findings to fixer, show FIXES to user.

### Step 11. Finalize

**hg skip**: Detect VCS with `vcs=$(bash PLUGIN_ROOT/scripts/detect-vcs.sh)`. If `vcs` is `hg`, skip this entire step. Report to user: "hg detected — skipping finalize (git-only). Override `prompts/finalizer.md` via `.codex/exec-plan/` to enable hg-native finalize." Note that `DEFAULT_BRANCH` substitutes as whatever detect-branch.sh returned — `remote/master` (or `remote/main`/`remote/trunk`) in modern-Mercurial repos that expose remote-tracking refs, `default` in repos that use the traditional named-branch convention — so any `git rebase origin/DEFAULT_BRANCH` in the bundled template must be replaced with the hg equivalent (e.g. `hg rebase -d remote/master`, or `hg rebase -d default` in the named-branch case) in the override. Proceed directly to step 12.

Check `finalize_enabled` loaded configuration (default: true). If false, skip this step.

After all reviews pass, rebase and clean up commits.

Report to user: "--- Finalize: rebase and clean up commits ---"

Spawn one authorized Codex subagent with the prompt from `prompts/finalizer.md`, applying Subagent Model. Replace `DEFAULT_BRANCH`, `PLAN_FILE_PATH`, and `PROGRESS_FILE_PATH`.

This is best-effort — if rebase fails, report the issue but don't block completion.

### Step 12. Stats summary

After finalize (or after Step 11 was skipped on hg/disabled), resolve `prompts/stats.md`. Substitute `DEFAULT_BRANCH` and `PROGRESS_FILE_PATH`. Use an authorized read-only Codex subagent, applying Subagent Model. When delegation is unavailable, use the parent only under the fallback rules in Codex Delegation and Subagent Model.

Use actual session/subagent metrics exposed by the current client and VCS statistics. Do not read Claude Code's session-log directory or assume Codex has the same log schema. Unavailable metrics are `n/a`; do not estimate them from filesystem timestamps.

Show the stats report to the user verbatim. This step is best-effort: report failure without blocking implementation completion.

### Step 13. Completion

When stats summary is done (or skipped on failure), report the actual task, validation, and review states. Unresolved blocking findings or failed/skipped required reviews keep the plan pending unless the user accepts the omission:
- **Report autonomous decisions and deviations to the user.** The run had no human to answer questions, so subagents decided judgment calls themselves and logged them. Collect every such entry from the progress file — `grep -E '^(\[[^]]*\] )?\[(decision|deviation)\]' <progress-file>` — and present them in a dedicated section titled **"Decisions made autonomously / Deviations from the plan"**, one bullet per entry with its stated reason, so the user learns every question the run answered on its own and why. If there are none, state "no autonomous decisions or deviations were logged." Do this regardless of whether finalize ran — finalize is skipped on hg or when disabled, so this is the guaranteed place the user always gets the report.
- Log actual completion or unresolved status to progress file; use the completion marker only when successful: `bash PLUGIN_ROOT/scripts/append-progress.sh <progress-file> "completed"`
- Only when implementation, required validation, and reviews are complete, move the finished plan into its `completed/` subdirectory and commit it (best-effort). Complete any deferred relocation checkbox at this step, restoring its unchecked state if the move fails: `bash PLUGIN_ROOT/scripts/move-plan.sh <plan-file-path>`. The script is a no-op when the plan is already under `completed/` or missing, derives the target as a `completed/` sibling of the plan's directory (so it respects a custom `plans_dir` and worktrees), and commits the move VCS-aware (git/hg). Do NOT push. If the script exits non-zero, report the failure but do not block completion.
- Report the final line "All N tasks completed, reviews passed, branch finalized" only when all three statements are true; otherwise state the actual outcome and remaining work. Append ", plan moved to completed/" ONLY when move-plan.sh actually moved the file (it printed `moved plan to ...`); omit the suffix when the move was a no-op (already under `completed/` or missing) or exited non-zero

## Key rules

- Each subagent gets a fresh context — no accumulated state from previous tasks
- Parent session only tracks: task number, success/failure, retry count
- Plan file is the single source of truth for progress — always re-read it
- No signals — just checkboxes in the plan for task progress
- Maintain progress file (`/tmp/progress-<plan-name>.txt`) — see `prompts/progress-file.md` for format and when to write
- Do not modify the plan file yourself during the task, review, and finalize phases — only subagents modify it. The sole exception is the terminal move in step 13 (after all phases finish), which the orchestrator performs via `move-plan.sh`
- Do not implement or fix code yourself — only subagents implement and fix
- If a subagent fails or leaves broken code, re-run the loop — do NOT investigate or fix it yourself
- NEVER dismiss findings as "pre-existing", "not from changes", or "architectural" — ALL findings are actionable
- NEVER summarize or filter agent findings — pass the full output to the fixer agent verbatim
- All prompt and agent files MUST be resolved through the three-layer override chain before use
- Use the available Codex subagent interface — resolved agent files provide the specialized prompt. Apply Subagent Model on every launch; do not pin another model or reasoning effort without user configuration/instructions
- After reading a prompt file, substitute all placeholders before passing to subagent (see Placeholder Substitution)
- Subagents run with NO human available — they must NEVER ask the user a question (no user-input tools, no pausing for routine implementation decisions). They decide judgment calls the plan does not settle from the project's lint rules, AGENTS.md, and code conventions, and log each as a `[decision]`/`[deviation]` line for the completion report
- In worktree mode (`worktree_mode = true`) the main working directory is never touched — no branch is created or checked out there and no changes land there; all git operations run inside the worktree, and Step 4's create-branch.sh is skipped

Missing authorization or an unavailable permission is a blocker to report to the parent, not a reason to bypass client controls. Preserve unrelated user changes and staged paths throughout execution.
