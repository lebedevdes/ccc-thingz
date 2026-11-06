---
name: planning-exec
description: "Execute plan tasks sequentially using subagents. Use when user says 'exec', 'execute plan', 'run plan', or wants to implement a plan file task by task with isolated subagents."
---

# exec

Execute plan file tasks sequentially, each in an isolated subagent.

## Arguments

- the user's arguments — path to plan file (optional; if omitted, ask user to pick from `docs/plans/`)

## OpenCode Setup

OpenCode supplies this skill's base directory as `SKILL_DIR`. The bundle root is two directories above it; resolve that to an absolute path and keep it as `PLUGIN_ROOT`. These are prompt placeholders, not environment variables supplied by OpenCode. Run `python3 "PLUGIN_ROOT/scripts/planning_config.py"` with `shell` from the active project root. Keep the returned settings and `plugin_data_dir` as `PLUGIN_DATA_DIR`. Quote paths in shell calls. For configuration requests, read `PLUGIN_ROOT/references/configuration.md`.

Use OpenCode **2.2.5+** tools: `read`, `write`/`edit` (or `patch` when available), `glob`, `grep`, `shell`, `question`, and `subagent`. Do not use OpenCode 1's `task`/`bash` APIs. Every child receives the absolute `WORKING_DIRECTORY`, plan/progress paths, bundle root, loaded settings, and a complete resolved prompt. Prepend to each child: "Work from WORKING_DIRECTORY; set the shell tool's `workdir` to that directory. Do not operate in the original checkout when worktree mode is active." New tasks/reviewers/fixers start fresh children; do not pass a prior `sessionID`. Child sessions share the working tree, not their conversation context. Keep all fanout in this parent session.

Do not set Claude Code's `bypassPermissions`: OpenCode's configured permissions apply. Reuse an existing user choice or authorization. Otherwise use `question` and wait; if unavailable in this client, ask in conversation and stop until answered. Child agents must return permission failures to the parent instead of waiting for user input or bypassing a denial.

## File Resolution

ALWAYS use the resolve script to read prompt and agent files. NEVER construct the override chain manually:
```
bash "SKILL_DIR/scripts/resolve-file.sh" prompts/task.md "PLUGIN_DATA_DIR"
bash "SKILL_DIR/scripts/resolve-file.sh" agents/quality.txt "PLUGIN_DATA_DIR"
```
The script checks project overrides, user overrides, and bundled defaults automatically.

### Placeholder Substitution

After reading a prompt file, replace ALL placeholders with actual values before passing to a subagent. Subagents run in fresh contexts without plugin env vars.

Always substitute: `PLAN_FILE_PATH`, `PROGRESS_FILE_PATH`, `DEFAULT_BRANCH`, `PLUGIN_ROOT` (resolve to actual absolute path), `RESOLVE_SCRIPT` (absolute path to `SKILL_DIR/scripts/resolve-file.sh`), `SKILL_DIR` (absolute skill base directory), `PLUGIN_DATA_DIR` (resolved user data directory — passed as second argument to resolve-file.sh so it can find user overrides), `WORKING_DIRECTORY` (active absolute project/worktree root), `USER_RULES` (resolved custom rules content from the rules loading step, or empty string if no rules found), and phase-specific values (`FINDINGS_LIST`, `REVIEW_PHASE`, `DIFF_COMMAND`).

## Custom Rules Loading

Before starting execution, run this command via shell tool to check for user-provided custom rules:

```bash
bash "PLUGIN_ROOT/scripts/resolve-rules.sh" planning-rules.md "PLUGIN_DATA_DIR"
```

If the output is non-empty, store it as the resolved custom rules content. When substituting `USER_RULES` in task prompts, wrap the content with a label so the subagent understands it: use "ADDITIONAL CUSTOM RULES:\n<content>" as the substitution. If the output is empty, substitute an empty string for `USER_RULES`. See `PLUGIN_ROOT/references/custom-rules.md` for full documentation on the rules mechanism.

## Subagent Model

Read `subagent_model` from the loaded configuration once and keep it as `SUBAGENT_MODEL`. Empty means omit the override and use OpenCode's configured model/inheritance. A configured value uses `provider/model` with an optional `#variant`, not Claude aliases such as `opus`.

Pass the configured override through the native `subagent` tool's model option when available in the advertised tool schema. If the client cannot apply it, stop and report that limitation rather than silently changing models. This applies to every task, reviewer, fixer, smells, finalizer and stats child. External review still runs through `run-external-review.sh` and is unaffected.

## Process

### Step 1. Resolve plan file

If the user supplied a plan file path, use it. Otherwise, list `.md` files in `docs/plans/`, excluding `completed/`. If exactly one plan found, use it automatically. If multiple found, ask the user to pick one using question.

Read the plan file. Count total Task sections (`### Task N:` or `### Iteration N:`) to know the scope.

Determine the default branch: `bash "SKILL_DIR/scripts/detect-branch.sh"`

Note: in `hg` repos, detect-branch.sh returns `remote/<name>` (checking `master`, `main`, `trunk` in that order) in modern-Mercurial repos that expose upstream default via `remote/<name>` refs, and falls back to `default` in repos that use the traditional named-branch convention instead. The external-review prompt (`prompts/codex-review.md`) and the finalize prompt (`prompts/finalizer.md`) use git-specific commands and are not VCS-translated upstream. Both phases will be skipped (see step 9 and step 11, which re-detect VCS locally). Users who want hg-native review/finalize can override via `.opencode/exec-plan/prompts/codex-review.md` and `.opencode/exec-plan/prompts/finalizer.md` — any `git rebase origin/DEFAULT_BRANCH` in the bundled template must be replaced with the hg equivalent in the override, e.g. `hg rebase -d remote/master` when the repo exposes remote-tracking refs, or `hg rebase -d default` when it uses the traditional named-branch convention.

### Step 2. Ask about worktree isolation

**hg skip**: Detect VCS with `vcs=$(bash "SKILL_DIR/scripts/detect-vcs.sh")`. If `vcs` is `hg`, skip the worktree question and proceed in current directory. Git worktrees have no direct hg equivalent here; users who want isolation in hg repos can use `hg share` manually before invoking `/exec`.

First detect current branch state — run `git branch --show-current` and compare with the default branch detected earlier (from `detect-branch.sh`). Two cases:

**Case A — currently on the default branch (master/main/trunk).** Step 4 will create a new feature branch. Ask the user where it should live. Invoke the **question** tool with this payload:

```json
{
  "questions": [{
    "question": "Where should the feature branch be created?",
    "header": "Branch location",
    "options": [
      {"label": "Worktree (isolated)", "description": "Create the feature branch in a new isolated git worktree (in a separate directory). Main working directory stays on the default branch."},
      {"label": "In-place", "description": "Create the feature branch in this working directory. Main directory switches to the feature branch for the duration of the run."}
    ],
    "multiple": false
  }]
}
```

**Case B — currently on a feature branch.** Step 4 will keep using this branch. Ask whether to move it to an isolated worktree or stay here. Invoke the **question** tool with this payload:

```json
{
  "questions": [{
    "question": "You're already on a feature branch. Run the plan here, or in an isolated worktree?",
    "header": "Isolation",
    "options": [
      {"label": "Stay here", "description": "Run the plan in this working directory, on the existing feature branch."},
      {"label": "Move to worktree", "description": "Copy this branch into a new isolated git worktree (in a separate directory). Main directory stays untouched."}
    ],
    "multiple": false
  }]
}
```

In BOTH cases: invoke the `question` tool **now**, do not generate text first, do not skip, do not assume. Auto mode does NOT exempt this question — the choice affects the user's working directory and the orchestrator cannot decide on their behalf.

**If the user picks "Worktree (isolated)" or "Move to worktree"** — the main working directory MUST NOT be touched at all: no branch is created or checked out there, and no file changes land there. That isolation is the entire point of this mode. Set `worktree_mode = true` and do this:

1. Record the original checkout's absolute root, current branch, HEAD and existing changed paths. Resolve any uncommitted source changes required by the plan with the user; a new/modified plan can be carried explicitly.
2. Derive the branch name without side effects: `bash "SKILL_DIR/scripts/create-branch.sh" --print-name <plan-file-path>`. If it already exists, choose a fresh name; never check out or repurpose that branch silently.
3. Create the worktree directly from current HEAD with `git worktree add -b <name> <absolute-worktree-path> HEAD`, in a separate directory outside the original checkout. Do not create or check out a branch in the original checkout first. Record `worktree_path` and `<name>`.
4. Resolve the plan path inside the worktree. If it was untracked/modified, copy only the selected plan, preserving its project-relative path. Carry the already loaded settings/rules and deliberately configured overrides; if they are untracked, copy only `.opencode/planning.json`, `.opencode/planning-rules.md`, and `.opencode/exec-plan/` as needed. Do not copy the whole configuration directory or overwrite different tracked settings.
5. Move this OpenCode session to the new directory using `opencode.session_move` through `execute` if available. The move takes effect at a safe boundary: perform destination-dependent work in a **later tool call**, then verify the active directory. If session moving is unavailable, stop and ask the user to open/resume the run there; a one-off `cd` does not relocate child sessions. Always pass the absolute active directory to children and set the shell tool's `workdir`.
6. **Step 4 is SKIPPED**: the branch already exists inside the worktree. Verify the original checkout's branch, HEAD and tracked contents remain unchanged; stop on an isolation breach.
7. Every later operation, including the plan move, runs inside the worktree. At completion report `worktree_path` and `<name>`; do not remove it or push automatically.

**If the user picks "In-place" or "Stay here"** — set `worktree_mode = false` and proceed normally; Step 4 creates the branch in this working directory.

### Step 3. Create task list

Create a visible task list with one entry per plan Task/Iteration section, then the original review/finalization stages:

- Review phase 1: comprehensive (5 parallel specialists, then fixer)
- Review phase 2: code smells (one specialist, then fixer)
- Review phase 3: external (adversarial review loop)
- Review phase 4: critical only (2 specialists, then fixer)
- Finalize (rebase, organize commits, verify)
- Stats summary

Use a native task-list tool only if the current client exposes one. OpenCode 2 does not require Claude Code's TaskCreate/TaskUpdate API. Otherwise track stage statuses in the conversation and the progress file after step 5 initializes it; the plan's checkboxes remain the source of truth for implementation progress. Distinguish completed, skipped, failed and max-iterations stages.

### Step 4. Create branch

**Skip this step entirely when `worktree_mode` is true** — Step 2 already created the branch (`<name>`) inside the isolated worktree, and running this here would `git checkout -b` in the main working tree and break isolation. Carry `<name>` forward as the branch name and go to Step 5.

Otherwise (in-place mode), **MANDATORY**: run the script below. Do NOT create the branch manually — the script strips the date prefix from the plan filename (e.g., `20260329-feature-name.md` → branch `feature-name`).

```
bash "SKILL_DIR/scripts/create-branch.sh" <plan-file-path>
```

The script creates a feature branch if currently on main/master, or stays on the current branch if already on a feature branch. Capture and use the branch name it outputs.

### Step 5. Initialize progress file

Initialize the progress file: `bash "SKILL_DIR/scripts/init-progress.sh" /tmp/progress-<plan-name>.txt <plan-file-path> <branch-name>` (derive `<plan-name>` from the plan file stem, e.g., `fix-issues.md` → `progress-fix-issues`). The script creates the file with a header. Report the full progress file path to the user.

IMPORTANT: Always use `"SKILL_DIR/scripts/append-progress.sh"` to write to the progress file after initialization. Never write directly.

### Step 6. Task loop

Repeat until no `[ ]` checkboxes remain in any Task section:

1. **Re-read the plan file** (subagent modifies it each iteration)
2. **Find the first Task section** (`### Task N:` or `### Iteration N:`) that still has `[ ]` checkboxes
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
5. **Spawn a subagent** using `subagent` with:
   - `agent: "general"`, a short `description`, and the fully resolved `prompt`
   - foreground execution (wait for the result); do not reuse a `sessionID`
   - `model: SUBAGENT_MODEL` when non-empty (see Subagent Model)
   - The task prompt from `prompts/task.md`, with all placeholders substituted as described in the Placeholder Substitution section above (including `USER_RULES`)
6. **After subagent returns**, re-read the plan file and check if that task's checkboxes are now `[x]`
   - If yes — task succeeded, continue loop
   - If no — **retry** with a fresh subagent for the same task up to `task_retries` times (planning configuration, default: 1). If all retries fail, stop and report failure to user
7. **Report to user**: "Task N completed" (one line). The task subagent logs details to the progress file.

CRITICAL: Spawn exactly ONE task subagent per iteration and WAIT for it to return before starting the next. NEVER batch-spawn multiple task subagents in a single message. Plan tasks are ordered and interdependent — later tasks build on the files earlier tasks create, and every task subagent edits the same plan-file checkboxes and overlapping source files, so running them in parallel corrupts the plan and the working tree. The "launch in a single message for parallel execution" instruction applies ONLY to the review phases (steps 7 and 10), never to this task loop.

CRITICAL: Do NOT stop the loop based on subagent return text. The ONLY condition to stop is: no `[ ]` checkboxes remain in any Task section (`### Task N:` or `### Iteration N:`). Always re-read the plan file to check.

CRITICAL: You are the ORCHESTRATOR. Never read code, debug errors, investigate diagnostics, or fix issues yourself. If a subagent leaves problems (compiler errors, test failures, lint issues), retry with a fresh subagent — pass the error details in the prompt so it can fix them. All code work happens inside subagents, not in the orchestrator.

Maximum iterations safety limit: 50. If reached, stop and report to user.

### Step 7. Review phase 1 — comprehensive then critical re-check

After all tasks complete, run a comprehensive code review on iteration 1, then narrow to critical-only re-checks on subsequent iterations to verify the fixer's work without re-running the full heavy sweep.

Report to user: "--- Review phase 1: comprehensive ---"

Loop up to `review_iterations` times (planning configuration, default: 5). Track the current iteration number:

1. **Read review.md as a playbook (NOT as a subagent prompt)** — resolve `prompts/review.md` through the override chain and read it from this main session. It tells YOU (the orchestrator) which specialist agents to fan out for the current `REVIEW_PHASE`. Substitute `DEFAULT_BRANCH`, `PLAN_FILE_PATH`, `PROGRESS_FILE_PATH`, `PLUGIN_ROOT`, and `REVIEW_PHASE` in the resolved content. Then follow the playbook FROM THIS SESSION: launch the specified independent `subagent` calls in a single assistant step for parallel execution; wait for all of them before any fixer writes. Subagents do not have the `subagent` tool, so the fanout MUST be initiated from the main orchestrator.
   - **Iteration 1**: set `REVIEW_PHASE` to `comprehensive`. Per the playbook, launch 5 parallel review agents (quality, implementation, testing, simplification, documentation).
   - **Iteration 2 and later**: set `REVIEW_PHASE` to `critical`. Per the playbook, launch 2 parallel review agents (quality, implementation) focused on critical/major issues only. Before this iteration, report to user: "--- Review phase 1: critical re-check (iteration N) ---"

2. **Collect findings** — collect findings from ALL launched review agents. Pass the COMPLETE output (not a summary) to the fixer. Do NOT summarize, filter, or dismiss any findings. ALL findings are actionable. Report to user with a short list of findings. Log to progress file:
   `bash "SKILL_DIR/scripts/append-progress.sh" <progress-file> "review phase 1: findings"`
   Then pipe: `echo "<findings>" | bash "SKILL_DIR/scripts/append-progress.sh" <progress-file>`

3. **If ALL agents reported zero issues** → report "Review phase 1: clean" and proceed to the next phase.

4. **Spawn a fixer agent** — resolve `prompts/fixer.md` through the override chain. Launch with `agent: "general"`, `model: SUBAGENT_MODEL` when non-empty. Pass the FULL unedited review output as FINDINGS_LIST — the fixer decides what's real, not you.

5. **After fixer returns** → show the "FIXES:" section to the user. Report "Review phase 1: iteration N fixes applied". Check for uncommitted changes: detect VCS with `vcs=$(bash "SKILL_DIR/scripts/detect-vcs.sh")`, then run `git status --porcelain` for `git` or `hg status` for `hg`. If output is non-empty, show every reported path and warn that these uncommitted changes are absent from the committed branch diff used by the next review. This is report-only: do not retry, abort, or commit leftovers because of this check. Loop back to step 1.

If `review_iterations` reached with issues still found, report "Review phase 1: max iterations reached, moving on" and continue.

### Step 8. Review phase 2 — code smells

Report to user: "--- Review phase 2: code smells analysis ---"

Run once (no loop):

1. **Spawn a smells agent** — resolve `agents/smells.txt` through the override chain. Launch one `subagent` call with `agent: "general"`, `model: SUBAGENT_MODEL` when non-empty, and the resolved agent prompt.

2. **Collect findings** — after the agent returns, report to user with a compact list of findings (one line per finding). Log findings to progress file:
   `bash "SKILL_DIR/scripts/append-progress.sh" <progress-file> "review phase 2: findings"`
   Then pipe the findings: `echo "<findings>" | bash "SKILL_DIR/scripts/append-progress.sh" <progress-file>`

3. **If no issues found** → report "Smells analysis: clean" and proceed to the next phase.

4. **Spawn a fixer agent** — resolve `prompts/fixer.md` through the override chain. Launch with `agent: "general"`, `model: SUBAGENT_MODEL` when non-empty. Pass the FULL smells output as FINDINGS_LIST.

5. **After fixer returns** → report fixes to user. Check for uncommitted changes: detect VCS with `vcs=$(bash "SKILL_DIR/scripts/detect-vcs.sh")`, then run `git status --porcelain` for `git` or `hg status` for `hg`. If output is non-empty, show every reported path and warn that these uncommitted changes are absent from the committed branch diff used by the next review. This is report-only: do not retry, abort, or commit leftovers because of this check. Proceed to the next phase.

### Step 9. Review phase 3 — external review

**hg skip**: Detect VCS with `vcs=$(bash "SKILL_DIR/scripts/detect-vcs.sh")`. If `vcs` is `hg`, skip this entire step. Report to user: "hg detected — skipping external review (git-only). Override `prompts/codex-review.md` via `.opencode/exec-plan/` to enable hg-native review." Proceed directly to step 10.

Report to user: "--- Review phase 3: external review ---"

Adversarial loop: the external reviewer reviews the code, fixer evaluates and fixes, the reviewer re-reviews. The loop exits early once an iteration produces no `CRITICAL` or `MAJOR` findings — minor-only iterations still get fixed by the fixer, but no further round-trip happens. Subsequent phases (smells, critical-only) act as the final safety net.

All invocations go through `run-external-review.sh`, which takes the `external_review_cmd` planning configuration value as its first argument and the prompt as its second. An empty first argument makes it fall back to codex. Do NOT call `run-codex.sh` directly — it cannot honor `external_review_cmd`. Older `codex-review.md` overrides may carry launcher or availability instructions before `## Prompt`; ignore those operational lines. Step 9 alone controls reviewer invocation and skip/failure handling.

If the script exits 127 AND the `.err` file from item 2 carries the `run-external-review:` marker, no external tool is available: report `External review: skipped — <that marker line>`, quoting the reason verbatim (it distinguishes a configured command missing from `PATH` from codex missing with no command set), and proceed to step 10. A 127 without that marker came from the reviewer itself — typically a wrapper script whose own inner tool is missing — and is a reviewer failure, not a skip.

Any other non-zero exit is a reviewer failure too, not a clean review: report `External review: reviewer failed (exit <code>) — <last line of the .err file>` and proceed to step 10. So is an exit 0 with empty stdout: report `External review: reviewer failed (no output)`, adding the last line of the `.err` file when it has one. Never treat empty output as "no findings" — the severity scan in item 4 would find nothing and the phase would report success without a review having run. Findings and the clean marker are judged on stdout only: codex echoes the whole prompt on stderr, severity definitions included, so a scan over stderr would read every clean review as blocking findings. A reviewer whose only output is on stderr, with no findings and no `NO ISSUES FOUND` marker on stdout, is a reviewer failure as well.

Loop up to `external_review_iterations` times (planning configuration, default: 10):

1. **Resolve the review prompt** — read `prompts/codex-review.md` through the override chain. Replace `DIFF_COMMAND` using `vcs=$(bash "SKILL_DIR/scripts/detect-vcs.sh")`: for `git`, every iteration uses `git diff DEFAULT_BRANCH...HEAD`; for `hg`, every iteration uses `hg diff -r 'ancestor(., DEFAULT_BRANCH)'`. Fixers commit their changes, so later reviews must include the committed branch diff. Also replace `PLAN_FILE_PATH` (so the reviewer can read the plan for intent) and `PROGRESS_FILE_PATH` (so the reviewer can read prior review iterations and fixer responses and avoid re-reporting fixed issues).

2. **Run the external reviewer** — first write the resolved prompt to `/tmp/external-review-<plan-name>.txt` with the `write` tool (same `<plan-name>` as the progress file, overwrite it each iteration), then run `python3 "PLUGIN_ROOT/scripts/run-review.py" "/tmp/external-review-<plan-name>.txt" 2>"/tmp/external-review-<plan-name>.err"` with `background: true` and `timeout: 600000`, so the task output holds the reviewer's stdout alone. Do NOT paste the prompt text inline: it contains backticks and may contain `$` (the bundled prompt asks for findings formatted as `` `SEVERITY: file:line - description` ``), and the shell would run those as command substitutions before the reviewer saw the prompt. Write the file with the `write` tool for that same reason — `echo "…" >` or a heredoc with an unquoted delimiter expands the backticks and `$` at write time, so the file the reviewer reads already has the format instruction blanked out. You will be notified when done — do NOT poll or sleep.

   The Python adapter loads the validated configuration and prompt file, then execs the original shell launcher with separate argv values; neither becomes shell code. Do not paste either into shell source or use `eval`. The shell tool's `workdir` must be the active project/worktree directory. Keep the loaded external reviewer choice fixed for the run; when using a worktree, carry the selected project configuration there before running this command. An interrupted/timed-out reviewer is a failure, even when partial stdout looks clean. Wait for the shell completion notification before reading results.

3. **Check the output** — the `NO ISSUES FOUND` marker counts as clean only when item 4's severity scan also comes back empty, so run that scan first. Marker present and no `CRITICAL` or `MAJOR` found → phase is done, proceed to step 10. That marker is the only clean result — the contract makes it mandatory — so never infer "clean" from output that lacks it. But the marker alone does not make a review clean either: a reviewer that echoes the phrase while still reporting a blocking finding is treated like any other finding output, and the findings win. Non-empty output without the marker must carry at least one `CRITICAL`, `MAJOR` or `MINOR` tag somewhere in stdout — a tag is what makes the output a review rather than a message. Output with neither the marker nor any tag is a reviewer failure: report `External review: reviewer failed (no findings and no clean marker)`, quoting the reviewer's first output line, and proceed to step 10. This is a whole-output check, not a per-line one — do not require every line to be tagged, or wrapped descriptions and blank separators would fail a real review. Output that clears this gate falls through to item 4 for severity classification.

4. **Classify severity** — scan the reviewer's stdout for `CRITICAL` or `MAJOR` markers (case-insensitive whole-word match). Set `has_blocking = true` if either is present, otherwise `has_blocking = false`. Findings without an explicit severity tag are treated as MINOR — `has_blocking` stays false in that case. That default applies to untagged lines sitting alongside at least one tagged line; item 3 has already rejected output carrying no tag at all, so it can never make an untagged non-review read as minor findings.

5. **Report findings to user** — show a compact list (one line per finding).

6. **Spawn a fixer agent** — same as other review phases, with `description: "Fixer - external review"` so the stats phase can group this run under review phase 3. Resolve `prompts/fixer.md`, pass the reviewer's stdout as FINDINGS_LIST. Fixer verifies, fixes, commits, reports FIXES.

7. **Report fixer results to user** - show FIXES section. Log to progress file. Check for uncommitted changes: detect VCS with `vcs=$(bash "SKILL_DIR/scripts/detect-vcs.sh")`, then run `git status --porcelain` for `git` or `hg status` for `hg`. If output is non-empty, show every reported path and warn that these uncommitted changes are absent from the committed branch diff used by the next review. This is report-only: do not retry, abort, or commit leftovers because of this check.

8. **Decide whether to loop**:
   - If `has_blocking` is false → report "External review: only minor findings — fixes applied, stopping loop" and proceed to step 10.
   - Otherwise → loop back to step 1.

If `external_review_iterations` reached with critical/major issues still found, report "External review: max iterations reached, moving on" and continue.

### Step 10. Review phase 4 — critical only

Report to user: "--- Review phase 4: critical/major only (single pass) ---"

Same structure as step 7 but with `REVIEW_PHASE` set to `critical`. Resolve `prompts/review.md` and follow its playbook FROM THIS MAIN SESSION — launch 2 parallel review agents (quality, implementation) focusing on critical/major issues only. Subagents do not have the `subagent` tool, so the fanout MUST be initiated from the main orchestrator. Same fixer flow — pass findings to fixer, show FIXES to user.

### Step 11. Finalize

**hg skip**: Detect VCS with `vcs=$(bash "SKILL_DIR/scripts/detect-vcs.sh")`. If `vcs` is `hg`, skip this entire step. Report to user: "hg detected — skipping finalize (git-only). Override `prompts/finalizer.md` via `.opencode/exec-plan/` to enable hg-native finalize." Note that `DEFAULT_BRANCH` substitutes as whatever detect-branch.sh returned — `remote/master` (or `remote/main`/`remote/trunk`) in modern-Mercurial repos that expose remote-tracking refs, `default` in repos that use the traditional named-branch convention — so any `git rebase origin/DEFAULT_BRANCH` in the bundled template must be replaced with the hg equivalent (e.g. `hg rebase -d remote/master`, or `hg rebase -d default` in the named-branch case) in the override. Proceed directly to step 12.

Check `finalize_enabled` planning configuration (default: true). If false, skip this step.

After all reviews pass, rebase and clean up commits.

Report to user: "--- Finalize: rebase and clean up commits ---"

Make one `subagent` call with `agent: "general"`, `model: SUBAGENT_MODEL` when non-empty, and the prompt from `prompts/finalizer.md`. Replace `DEFAULT_BRANCH`, `PLAN_FILE_PATH`, and `PROGRESS_FILE_PATH`.

This is best-effort — if rebase fails, report the issue but don't block completion.

### Step 12. Stats summary

After finalize (or after step 11 was skipped on hg/disabled), make one `subagent` call with `agent: "general"`, `model: SUBAGENT_MODEL` when non-empty, and the prompt from `prompts/stats.md`. Replace `DEFAULT_BRANCH` and `PROGRESS_FILE_PATH` in the resolved content.

The stats agent uses actual OpenCode metrics only when supplied/exposed by this client, the progress file, and VCS stats. It must not read Claude Code JSONL logs or infer timing/tokens from file mtimes. Unavailable metrics are `n/a`.

Show the stats agent's full markdown output to the user verbatim. Do NOT summarize it further — the agent already produces a tight summary.

This step is best-effort — if the stats agent fails or client metrics are unavailable, report the failure but do not block completion.

### Step 13. Completion

When stats summary is done (or skipped on failure):
- **Report autonomous decisions and deviations to the user.** The run had no human to answer questions, so subagents decided judgment calls themselves and logged them. Collect every such entry from the progress file — `grep -E '^(\[[^]]*\] )?\[(decision|deviation)\]' <progress-file>` — and present them in a dedicated section titled **"Decisions made autonomously / Deviations from the plan"**, one bullet per entry with its stated reason, so the user learns every question the run answered on its own and why. If there are none, state "no autonomous decisions or deviations were logged." Do this regardless of whether finalize ran — finalize is skipped on hg or when disabled, so this is the guaranteed place the user always gets the report.
- Log completion to progress file: `bash "SKILL_DIR/scripts/append-progress.sh" <progress-file> "completed"`
- Move the finished plan into its `completed/` subdirectory and commit it (best-effort): `bash "SKILL_DIR/scripts/move-plan.sh" <plan-file-path>`. The script is a no-op when the plan is already under `completed/` or missing, derives the target as a `completed/` sibling of the plan's directory (so it respects the plan location and worktrees), and commits the move VCS-aware (git/hg). Do NOT push. If the script exits non-zero, report the failure but do not block completion.
- Report actual outcomes: tasks completed, each review passed/skipped/failed/max iterations, and whether finalization succeeded or was skipped. Say "reviews passed" or "branch finalized" only when those outcomes were verified. Append ", plan moved to completed/" ONLY when move-plan.sh actually moved the file (it printed `moved plan to ...`); omit the suffix when the move was a no-op (already under `completed/` or missing) or exited non-zero

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
- All execution/review child agent IDs are `general` — agent files provide the specialized prompt
- Every `subagent` call passes `model: SUBAGENT_MODEL`, and omits `model` when it is empty (see Subagent Model)
- After reading a prompt file, substitute all placeholders before passing to subagent (see Placeholder Substitution)
- Subagents run with NO human available — they must NEVER ask the user a question (no question, no pausing for input). They decide judgment calls the plan does not settle from the project's lint rules, AGENTS.md (or CLAUDE.md when that is the project instruction file), and code conventions, and log each as a `[decision]`/`[deviation]` line for the completion report
- In worktree mode (`worktree_mode = true`) the main working directory is never touched — no branch is created or checked out there and no changes land there; all git operations run inside the worktree, and Step 4's create-branch.sh is skipped
