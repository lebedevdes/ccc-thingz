# Planning Plugin Usage

The planning plugin has two skills: planning-make (plan creation) and planning-exec (autonomous execution), with internal plan-review and external OpenCode review prompts.

## Make — `$planning-make`

### Triggers
- `$planning-make <description>` — create an implementation plan
- invoked automatically by brainstorm when user picks "Write plan"

### Workflow
1. **Step 0** — parses intent (feature, bug fix, refactor, migration) and explores codebase for context
2. **Step 1** — asks focused questions one at a time: goal, scope, constraints, testing approach, title
3. **Step 1.5** — proposes 2-3 implementation approaches with trade-offs (skipped if obvious)
4. **Step 2** — creates plan file at `docs/plans/yyyymmdd-<task-name>.md`
5. **Step 3** — offers next steps: interactive review, auto review (plan-review agent or external reviewer), implement, or done

After creating the plan, the next-step choice is explicit unless the user already specified the action or requested a plan only. After either review, the same four choices are offered again, including the option to repeat a review or choose another reviewer. When a client cannot display all four options in its question widget, the skill presents a numbered question in conversation and waits for the answer. Creating or approving a plan alone does not authorize a commit or implementation.

### Examples
```
$planning-make add user authentication
$planning-make fix the race condition in the connection pool
$planning-make refactor the middleware stack
$planning-make add my Go testing rules to user-level planning rules
```

### Plan File Structure
- Overview, Context, Development Approach, Testing Strategy
- Implementation Steps with `### Task N:` sections
- Each task has `**Files:**` block and `[ ]` checkboxes
- Progress tracking with `[x]`, `➕`, `⚠️` markers

## Exec — `$planning-exec`

### Triggers
- `$planning-exec [plan-file]` — execute a plan autonomously
- "exec", "execute plan", "run plan"

### Workflow
1. Resolves plan file (from argument or picks from `docs/plans/`)
2. Asks about worktree isolation (worktree vs current directory)
3. Creates a feature branch
4. Executes tasks sequentially — one subagent per task, commits after each
5. Runs multi-phase review: comprehensive (iteration 1) then critical re-check loop → code smells → external review → critical-only
6. Optional finalize: rebase and squash commits
7. Stats summary: report available client metrics and VCS statistics; unavailable metrics are n/a

### Configuration
Load settings with `scripts/planning_config.py`: defaults, user `${CODEX_HOME:-$HOME/.codex}/planning.json`, project `.codex/planning.json`, then provider/model environment overrides. See [configuration.md](configuration.md).

| Key | Default | Description |
|-----|---------|-------------|
| `external_review_provider` | `deepseek` | OpenCode provider for both plan and code review |
| `external_review_model` | `deepseek-flash` | model ID within that provider |
| `external_review_timeout` | `600` | external review timeout in seconds |
| `opencode_command` | `["opencode", "--standalone"]` | configured OpenCode executable and arguments |
| `task_retries` | `1` | retries for failed tasks |
| `review_iterations` | `5` | max fix-and-recheck cycles |
| `external_review_iterations` | `10` | max external review iterations |
| `finalize_enabled` | `true` | run rebase + squash phase |
| `subagent_model` | `""` | model ID for all native exec subagents; empty keeps client defaults |
| `plans_dir` | `docs/plans` | directory for plan files |

### Customization
Prompts and agent definitions use a three-layer override chain:
1. Project: `.codex/exec-plan/prompts/` and `.codex/exec-plan/agents/`
2. User: `${CODEX_HOME:-$HOME/.codex}/exec-plan/prompts/` and `${CODEX_HOME:-$HOME/.codex}/exec-plan/agents/`
3. Bundled defaults

Nothing is copied anywhere automatically. Use `scripts/customize-file.sh <relative-path>` to copy an individual reference without overwriting an existing override. See [configuration.md](configuration.md) for commands and override behavior.

### Customization patterns

- *Customize review specialists.* Override `prompts/review.md` and the specialist prompts, using the Codex subagent interface available in the client.
- *Delegate to an existing skill.* Override a prompt or agent file to read another skill's `SKILL.md` and follow it inline. Examples: `agents/smells.txt` → an installed smells skill; `prompts/finalizer.md` → an installed commit-finalization skill.

### Subagent constraint

The main session follows `prompts/review.md` as a playbook and launches specialists with available, authorized Codex subagent tools. Batch reviewers to fit the client's concurrency limit and wait for readers before a fixer writes. Leaf workers do not delegate further. Apply `subagent_model` to every exec worker/reviewer/fixer launch. When an override is selected, use a fresh context if the client requires it and report unsupported model selection rather than silently switching models. With no override, unavailable delegation can fall back to checks in the parent, reported as non-independent passes.

## Plan-Review — agent

### Triggers
- launched by make's "Auto review" option when the user picks "Plan-review agent"
- resolve `prompts/internal-plan-review.md` and pass it to an available, authorized Codex subagent, or review in the current session if delegation is unavailable

### What It Checks
- problem definition and solution correctness
- scope creep and over-engineering
- testing requirements and coverage
- task granularity and ordering
- convention adherence (via AGENTS.md and custom rules)

### Output
Structured report with severity-rated findings:
- Critical Issues, Important Issues, Minor Issues
- Over-Engineering Concerns
- Testing Coverage Assessment
- Verdict: APPROVE or NEEDS REVISION

## External-Plan-Review — agent

### Triggers
- launched by make's "Auto review" option when the user picks "External reviewer"

### What It Does
- sends the plan to OpenCode through `scripts/run-external-review.py`, using the configured provider/model
- the reviewer reads the plan, AGENTS.md and the code it names, and reports wrong assumptions, missing steps, over-engineering and ordering problems
- one pass; make shows each finding with Codex's assessment and revises the plan for the ones the user selects

### Output
The runner returns `clean`, `findings`, `skipped`, or `failed` with the findings or failure details. See [external-review.md](external-review.md).

## Interactive Review

After creating a plan, make offers interactive review via:
- **revdiff** (if installed) — TUI with syntax highlighting and line-level annotations
- **plan-annotate.py** (fallback) — opens plan in `$EDITOR` via terminal overlay

Both loop until the user quits without annotations.

Questions follow the Questions in Codex rule in both skills. Run the bundled `scripts/question-environment.sh` in the skill directory to inspect the environment. For every single-choice question, use `agtermctl pick` first when the script reports a candidate, using the reported window and socket. If a sandbox restriction or likely sandbox-related socket error prevents the picker from opening, request elevated permissions and retry before falling back, subject to client permission policy. Use a supported client input form or a numbered question in conversation only when the picker is unavailable or fails after the applicable retry. The script cannot detect client-provided tools. Wait for the user's actual answer; cancellation is not an answer.
