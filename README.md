# cc-thingz

Things to make [Claude Code](https://claude.ai/code) even better — hooks, skills, and commands, organized as a marketplace of independent plugins.

This is an unapologetically opinionated set. Every skill here is something I actually use — some multiple times a day (brainstorm, plan, review), others less often but worth having in the toolbox. There are plenty of plugin collections out there, from random grab-bags to well-organized catalogs. This one is mine, and it reflects how I work. Even if you don't need my particular toolbox, it might give you ideas for building your own and making Claude Code do what you want it to do.

## OpenCode

The planning adaptation in `opencode_plugins/planning/` targets **OpenCode 2.2.5+**
and is based directly on the Claude Code planning plugin v3.12.0. It preserves
`/planning:make`, `/planning:exec`, the plan template, sequential fresh-context
task execution, four review phases, Codex external review by default, worktree
isolation, and optional finalization.

Install the planning command, exec skill and plan-review agents globally:

```bash
python3 opencode_plugins/planning/scripts/install.py
```

Or install into one project:

```bash
python3 opencode_plugins/planning/scripts/install.py --project /path/to/project
```

Then start OpenCode in the project and run:

```text
/planning:make add caching to the API
/planning:exec docs/plans/20261104-api-cache.md
```

The installer copies the entire bundle to `skills/planning/` and writes the two
command wrappers and two plan-review agents. Re-run it after upgrading to refresh
the managed copy and generated files; it overwrites only entries it owns and
refuses unrelated files. It does not edit OpenCode permissions, provider
credentials or preferences. Use `--dry-run` to preview.

Settings use `.opencode/planning.json` over user-level
`~/.config/opencode/planning.json`, with `OPENCODE_CONFIG_DIR` and `XDG_CONFIG_HOME`
support. The original settings minus `plans_dir` remain (six total);
`subagent_model` uses OpenCode's `provider/model` format. Plans always live in
`docs/plans/`. Rules and prompt overrides use OpenCode paths. The original
`ExitPlanMode` hook is not installed; make retains explicit revdiff/editor
annotation review. Missing session metrics are reported as `n/a`.

See the [OpenCode planning usage guide](opencode_plugins/planning/references/usage.md)
and [configuration reference](opencode_plugins/planning/references/configuration.md).
Run `bash tests/test-opencode-planning.sh` for temporary-fixture checks without
model calls or changes to personal configuration.

## Codex

Codex adaptations live in `codex_plugins/`, with a separate marketplace at
`.agents/plugins/marketplace.json`.

| Plugin | Skills | Purpose |
|---|---|---|
| brainstorm | `$brainstorm` | Explore an idea, compare approaches, and validate a design |
| planning | `$planning-make`, `$planning-exec` | Create implementation plans and execute them with Codex reviews and external OpenCode review |
| workflow | `$learn`, `$clarify`, `$wrong`, `$md-copy`, `$txt-copy`, `$backlog` | Capture project knowledge, explain behavior, reconsider an approach, copy text, and manage deferred work |
| thinking-tools | `$dialectic`, `$root-cause-investigator`, `$ask-opencode` | Test opposing hypotheses, investigate root causes, and get an OpenCode second opinion |

From the repository root, register the local marketplace and install the plugin:

```bash
codex plugin marketplace add .
codex plugin add brainstorm@ccc-thingz-codex
codex plugin add planning@ccc-thingz-codex
codex plugin add workflow@ccc-thingz-codex
codex plugin add thinking-tools@ccc-thingz-codex
```

After these changes are pushed, install from the fork instead:

```bash
codex plugin marketplace add lebedevdes/ccc-thingz
codex plugin add brainstorm@ccc-thingz-codex
codex plugin add planning@ccc-thingz-codex
codex plugin add workflow@ccc-thingz-codex
codex plugin add thinking-tools@ccc-thingz-codex
```

Start a new Codex session and invoke `$brainstorm`, for example:
`$brainstorm help me design caching for this API`. Natural-language brainstorm
requests can also select the skill. See the
[Codex usage guide](codex_plugins/brainstorm/skills/brainstorm/references/usage.md)
for workflow details and examples.

The Brainstorm adaptation for Codex is by Anton Lebedev, based on
[Brainstorm by Umputun](https://github.com/umputun/cc-thingz).
The original copyright notice and MIT license are preserved in the
[plugin license](codex_plugins/brainstorm/LICENSE).

The Codex version keeps the collaborative design workflow, uses the client's
available question tools (or ordinary conversation), and can write a plan
without requiring the Claude Code planning plugin. It loads custom rules from
`.codex/brainstorm-rules.md` in the project first, then
`${CODEX_HOME:-$HOME/.codex}/brainstorm-rules.md`; the first non-empty file wins.
The bundled `skills/brainstorm/scripts/resolve-rules.sh` performs this lookup.
See the [Codex custom rules reference](codex_plugins/brainstorm/skills/brainstorm/references/custom-rules.md).

The package uses a root `plugin.json` manifest and bundles its helper and
references inside the skill so they also work when the skill is installed alone.
For a manual install, copy `codex_plugins/brainstorm/skills/brainstorm/` to
`${CODEX_HOME:-$HOME/.codex}/skills/brainstorm/`, then start a new session. Choose
either plugin installation or manual skill installation to avoid duplicates.

Packaging follows the [official Codex plugin documentation](https://developers.openai.com/plugins/build/plugins).

To check the Codex rules resolver, run
`bash tests/test-codex-brainstorm-resolve-rules.sh`. It covers precedence, empty
files, `CODEX_HOME`, explicit user directories, and paths containing spaces;
the existing shell-test CI job runs it automatically.

### Planning in Codex

Start a new session after installing the planning plugin:

```text
$planning-make add caching to the API
$planning-exec docs/plans/20261103-api-cache.md
```

The Codex skills preserve the original planning workflows, plan template,
review checklists, and task/fixer/finalizer prompts. See the
[Codex planning usage guide](codex_plugins/planning/references/usage.md).

`planning-make` follows the original discovery, one-question-at-a-time context
collection, approach comparison, and plan creation steps. It offers interactive
annotations via `revdiff` or `$EDITOR`, the original internal plan-review checklist,
external OpenCode plan review, interactive/autonomous implementation, or a plan-only
finish. Selecting Implement or Done commits the selected plan as in the original,
while honoring prior instructions about commits.

`planning-exec` retains the original thirteen-step orchestration: resolve the plan,
choose worktree isolation, track tasks, create the branch, initialize progress,
execute one task at a time, run four review phases, finalize, report statistics,
and move the completed plan. Codex adaptations cover tool APIs, permissions,
concurrency, worktree handling, configuration, and available session metrics.
Reviewers use authorized Codex subagents, or disclosed sequential checks when
unavailable. OpenCode performs external review. Failed/skipped reviews and unresolved
work remain visible; final reports reflect the actual outcome. Finalization never
pushes.

`subagent_model` in project/user `planning.json` selects the model for all native
`planning-exec` subagents: tasks, review specialists, fixers, smells, finalizer,
and stats. Its default is `""`, which leaves model selection to the client.
A selected model is passed on each launch with a fresh context when required;
unsupported selections are reported without silently substituting another model.
Use a model ID available in your Codex client. OpenCode's reviewer model remains
configured separately through `external_review_model`.

External review defaults to **DeepSeek V4.1 Flash** through OpenCode:
provider `deepseek`, model `deepseek-flash`, selector `deepseek/deepseek-flash`.
Both plan review and code review use these same defaults. This model ID is
confirmed by the [DeepSeek API documentation](https://api-docs.deepseek.com/quick_start/pricing/).
OpenCode must be installed and authenticated for the selected provider.

To change provider/model, create `.codex/planning.json` in the project or
`${CODEX_HOME:-$HOME/.codex}/planning.json` for all projects:

```json
{
  "external_review_provider": "deepseek",
  "external_review_model": "deepseek-flash"
}
```

Settings merge by key: defaults → user → project. Environment variables
`PLANNING_EXTERNAL_REVIEW_PROVIDER` and `PLANNING_EXTERNAL_REVIEW_MODEL` override
both files. Other settings include task retries, review iteration limits,
timeout, plans directory, and finalization. The default OpenCode command is
`["opencode", "--standalone"]`; OpenCode 2.2.5+ is required. The helper first
resolves effective permissions with `debug agents`, then runs its
plan agent, supplies review instructions and the full code diff as an attachment,
and parses final JSON text events; empty output, errors, and timeouts do not count
as clean reviews. OpenCode's review process uses reading/search tools, with edits
and shell access disabled. Existing read/search restrictions are preserved;
operations requiring approval are denied in this noninteractive process. The
attachment includes separate staged/unstaged diffs and Git status so index-only
changes remain visible. Credentials stay in OpenCode's configuration.

Planning rules resolve from `.codex/planning-rules.md` first, then
`${CODEX_HOME:-$HOME/.codex}/planning-rules.md`. Prompt and specialist overrides
resolve from `.codex/exec-plan/`, then
`${CODEX_HOME:-$HOME/.codex}/exec-plan/`, then bundled references. The
`customize-file.sh` helper copies individual references without overwriting an
existing override. For settings, defaults, and customization details, see the
[Codex planning configuration](codex_plugins/planning/references/configuration.md).

The plugin bundles VCS/commit/progress helpers, an OpenCode review runner, and
explicit revdiff/editor launchers. It does not install Claude lifecycle hooks.
For manual installation, keep the entire `codex_plugins/planning/` directory
together and link its two skill directories into
`${CODEX_HOME:-$HOME/.codex}/skills/` using symlinks. When locating shared helpers,
resolve the real skill directory before walking to the plugin root. A copied
skill directory alone does not include the planning plugin's shared resources.

Run `bash tests/test-codex-planning.sh` to check configuration precedence,
provider/model selection, OpenCode output/error/timeout handling, full branch
snapshots, scoped plan commits, custom rules/overrides, and editor feedback.
These tests use temporary fixtures and fake OpenCode responses, so CI requires
no provider credentials or model calls. The regular shell-test CI job picks them
up automatically.

### Workflow in Codex

The workflow plugin contains six skills:

| Skill | Purpose |
|---|---|
| `$learn` | Save selected reusable discoveries to project guidance or an established knowledge store |
| `$clarify` | Investigate unexpected behavior and explain it with code/configuration evidence |
| `$wrong` | Reconsider a failed approach, compare alternatives, and continue in the agreed direction |
| `$md-copy` | Format the selected answer as Markdown and copy it to the local clipboard |
| `$txt-copy` | Copy selected text without reformatting |
| `$backlog` | List, triage, add, fix, or drop deferred items in `docs/backlog/` |

Start a new session after installing the plugin. Examples:

```text
$learn save the project conventions we discovered
$clarify why does this setting have no effect?
$wrong reconsider the caching approach
$md-copy copy the last answer as Markdown
$txt-copy copy the email above
$backlog --all
$backlog stale-cache-invalidation
```

`learn` follows existing memory-placement guidance and defaults to `AGENTS.md`
for shared project knowledge. It accounts for active `AGENTS.override.md` files
and keeps personal notes in an established local destination. It does not create
a separate personal-memory convention or write global guidance automatically.
The choice follows the [official Codex instruction-discovery rules](https://learn.chatgpt.com/docs/agent-configuration/agents-md).

The workflow skills preserve the original Claude Code scenarios and steps, with
Codex adaptations for questions, planning, and instruction-file discovery.
Questions prefer a supported blocking input tool; asynchronous questions pause
the workflow until answered, and ordinary conversation is the fallback.
The skills honor decisions and authorization already given in the session.
`clarify` can use `planning-make` when installed, or plan directly; switching to
Plan mode is handled by the user when the client supports it.
`backlog` keeps the original Git-only, one-file-per-item format, `worth` triage,
slug/`--all` selection, deduplication, branch checks, and deletion with the fix.
Reading the backlog does not authorize fixes, commits, or pushes.

The copy skills use the original inline Bash mechanism: write a temporary text
file, copy through macOS `pbcopy` or X11 `xclip`/`xsel`, and remove the temporary
file. No Python clipboard helper is required at runtime.

For a manual install, copy the desired directories from
`codex_plugins/workflow/skills/` to `${CODEX_HOME:-$HOME/.codex}/skills/`.
All six skills are self-contained.

Run `bash tests/test-codex-workflow.sh` to exercise the inline copy commands with
fake clipboard tools. The tests cover backend selection, literal Unicode and
whitespace, and cleanup without changing the real clipboard.
The existing shell-test CI job runs them automatically.

### Thinking Tools in Codex

The thinking-tools skills preserve the original Claude Code workflows, templates, and examples,
with adaptations for Codex tools, invocation syntax, and OpenCode consultation:

- `$dialectic`: launch supporting and opposing agents, synthesize their findings,
  and verify against the implementation. Use available, authorized Codex subagent
  tools; identify a sequential fallback when parallel delegation is unavailable.
- `$root-cause-investigator`: the original five-level 5-Why investigation, with
  issue/analysis templates and the original diagnostic reference materials.
- `$ask-opencode`: the original consultation workflow adapted from `ask-codex`,
  including explicit triggers, escalation after 4+ failed attempts, prompt
  templates, adversarial review, and presentation of the external assessment.

Examples in a new session after installation:

```text
$dialectic this implementation is thread-safe
$root-cause-investigator investigate the intermittent connection timeout
$ask-opencode get a second opinion on why this test still fails
$ask-opencode review the changes on this branch
```

OpenCode consultation uses the same provider/model settings as planning:
`${CODEX_HOME:-$HOME/.codex}/planning.json`, then project `.codex/planning.json`,
with `PLANNING_EXTERNAL_REVIEW_PROVIDER` and `PLANNING_EXTERNAL_REVIEW_MODEL`
environment overrides. Defaults are `deepseek` / `deepseek-flash`
(DeepSeek V4.1 Flash), a 600-second timeout, and
`["opencode", "--standalone"]`. The plugin bundles its own reader/transport,
so **planning does not need to be installed** and the settings still work.
See [consultation settings and result handling](codex_plugins/thinking-tools/references/opencode.md).

The helper `scripts/ask-opencode.py` accepts a safely written prompt file,
optional repeated `--attach` context files, and `--diff-base` for a full Git
change snapshot. It extracts final assistant text, preserves the selected
provider configuration, disables editing/shell access in the consultation agent,
and reports missing tools, invalid output, errors, and timeouts explicitly.
Structured reviews follow the [review contract](codex_plugins/thinking-tools/references/review-contract.md).
Codex checks the external answer against the evidence and implements fixes only
within the user's authorized task. Review presentation follows the original
severity ordering and omits findings with confidence below 0.3; the helper retains
the full structured result.

For manual installation, `dialectic` can be copied as a single skill;
`root-cause-investigator` includes its `references/` directory. Keep the whole
`codex_plugins/thinking-tools/` folder together for `ask-opencode` and link its
skill directory into `${CODEX_HOME:-$HOME/.codex}/skills/` so it can locate the
shared helper/resources through its real path. The helpers require Python 3.10+.

Run `bash tests/test-codex-thinking-tools.sh` to check shared configuration,
advice/review output, provider/model selection, context/diff attachments, errors,
and timeout handling using fake OpenCode responses. CI makes no model calls.

## Claude Code Install

Add the marketplace, then install the plugins you want:

    /plugin marketplace add umputun/cc-thingz

    /plugin install brainstorm@umputun-cc-thingz
    /plugin install review@umputun-cc-thingz
    /plugin install planning@umputun-cc-thingz
    /plugin install release-tools@umputun-cc-thingz
    /plugin install thinking-tools@umputun-cc-thingz
    /plugin install skill-eval@umputun-cc-thingz
    /plugin install workflow@umputun-cc-thingz

Test a plugin locally:

    claude --plugin-dir plugins/brainstorm

<details>
<summary>Manual install (alternative)</summary>

Copy the files you want to your Claude Code config directory manually.

**brainstorm** — skill:
```bash
cp -r plugins/brainstorm/skills/brainstorm ~/.claude/skills/
cp -r plugins/brainstorm/scripts/ ~/.claude/skills/brainstorm/scripts
cp -r plugins/brainstorm/references/ ~/.claude/skills/brainstorm/references
```

Note: when installed manually, update `${CLAUDE_PLUGIN_ROOT}` references inside `brainstorm/SKILL.md` to use `~/.claude/skills/brainstorm` instead.

**review** — skills (review-pr + git-review + writing-style):
```bash
cp -r plugins/review/skills/pr ~/.claude/skills/
cp -r plugins/review/skills/git-review ~/.claude/skills/
cp -r plugins/review/skills/writing-style ~/.claude/skills/
chmod +x ~/.claude/skills/git-review/scripts/git-review.py
```

Note: update the `/review:writing-style` reference inside `pr/SKILL.md` to `/writing-style` when installed manually.

**planning** — command + exec skill + hook:
```bash
cp plugins/planning/commands/make.md ~/.claude/commands/
cp -r plugins/planning/skills/exec ~/.claude/skills/
cp -r plugins/planning/scripts/ ~/.claude/commands/scripts
cp -r plugins/planning/references/ ~/.claude/commands/references
cp plugins/planning/scripts/plan-annotate.py ~/.claude/scripts/
chmod +x ~/.claude/scripts/plan-annotate.py
chmod +x ~/.claude/skills/exec/scripts/*.sh
```

Note: when installed manually, update `${CLAUDE_PLUGIN_ROOT}` references inside `exec/SKILL.md`, `make.md`, and prompt files to use the appropriate local paths instead.

Add the plan-annotate hook to `~/.claude/settings.json`:
```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "ExitPlanMode",
      "hooks": [{
        "type": "command",
        "command": "~/.claude/scripts/plan-annotate.py",
        "timeout": 345600
      }]
    }]
  }
}
```

**release-tools** — skills + scripts:
```bash
cp -r plugins/release-tools/skills/new ~/.claude/skills/
cp -r plugins/release-tools/skills/last-tag ~/.claude/skills/
chmod +x ~/.claude/skills/new/scripts/*.sh
```

Note: when installed manually, update the `${CLAUDE_PLUGIN_ROOT}` references inside `new/SKILL.md` to use the appropriate local paths instead.

**thinking-tools** — skills:
```bash
cp -r plugins/thinking-tools/skills/ask-codex ~/.claude/skills/
cp -r plugins/thinking-tools/skills/dialectic ~/.claude/skills/
cp -r plugins/thinking-tools/skills/root-cause-investigator ~/.claude/skills/
```

**skill-eval** — hook:
```bash
cp plugins/skill-eval/hooks/skill-forced-eval-hook.sh ~/.claude/scripts/
chmod +x ~/.claude/scripts/skill-forced-eval-hook.sh
```

Add the skill-eval hook to `~/.claude/settings.json`:
```json
{
  "hooks": {
    "UserPromptSubmit": [{
      "hooks": [{
        "type": "command",
        "command": "~/.claude/scripts/skill-forced-eval-hook.sh"
      }]
    }]
  }
}
```

**workflow** — skills:
```bash
cp -r plugins/workflow/skills/learn ~/.claude/skills/
cp -r plugins/workflow/skills/clarify ~/.claude/skills/
cp -r plugins/workflow/skills/wrong ~/.claude/skills/
cp -r plugins/workflow/skills/md-copy ~/.claude/skills/
cp -r plugins/workflow/skills/txt-copy ~/.claude/skills/
cp -r plugins/workflow/skills/backlog ~/.claude/skills/
```

Note: the slug form taught inside `backlog/SKILL.md` is `/workflow:backlog <slug>`; it is `/backlog <slug>` when installed manually.

Restart Claude Code for changes to take effect.

</details>

## Updating plugins

The `/plugin` menu has two update paths, and they behave differently:

- `/plugin` → **Marketplaces** → **Update marketplace** — pulls the latest plugin catalog from the repo immediately. This is the reliable way to get updates.
- `/plugin` → **Installed** → **Update now** — uses a local cache that can be stale for a long time and may not reflect recent changes. Use this as a fallback after updating the marketplace.

To keep plugins current automatically, enable `/plugin` → **Marketplaces** → **Enable auto-update**. This updates the marketplace catalog on each session start.

## Plugins

| Plugin | Description |
|--------|-------------|
| [brainstorm](#brainstorm) | Collaborative design dialogue — idea to approaches to design to plan |
| [review](#review) | PR review + interactive git diff annotation review + writing style guide |
| [planning](#planning) | Structured implementation planning, interactive annotation review, and autonomous plan execution |
| [release-tools](#release-tools) | Release workflow — auto-versioning, release notes, changelog |
| [thinking-tools](#thinking-tools) | Analytical thinking — dialectic analysis, root cause investigation, codex consultation |
| [skill-eval](#skill-eval) | Forces skill evaluation before every response |
| [workflow](#workflow) | Session helpers and deferred-work backlog — knowledge capture, confusion handling, clipboard copy, backlog items |

### brainstorm

Collaborative design skill. Invoke with `/brainstorm:do` or trigger phrases like "brainstorm", "let's brainstorm", "help me design", "explore options for", etc.

| Component | Trigger | Description |
|-----------|---------|-------------|
| skill | `/brainstorm:do` | Collaborative design dialogue — idea → approaches → design → plan |

Guides a 4-phase dialogue to turn ideas into designs:

1. **Understand** — gathers project context, asks questions one at a time (multiple choice preferred)
2. **Explore Approaches** — proposes 2-3 options with trade-offs, leads with recommendation
3. **Present Design** — breaks design into sections of 200-300 words, validates each incrementally
4. **Next Steps** — offers to write a plan (`/planning:make`), enter plan mode, or start implementing

### review

PR review, interactive git diff annotation review, and writing style tools. Install together — review-pr uses writing-style for drafting comments.

| Component | Trigger | Description |
|-----------|---------|-------------|
| skill | `/review:pr <number>` | PR review with architecture analysis, scope creep detection, and merge workflow |
| skill | `/review:git-review [ref]` | Interactive git diff annotation review — editor overlay with feedback loop |
| skill | `/review:writing-style` | Direct technical communication — anti-AI-speak, brevity, no filler |

**review-pr** — analyzes code quality, architecture, test coverage, and identifies scope creep:
- **Phase 0** — detects PR vs issue (issues get a simpler comment-only flow)
- **Phase 1** — fetches PR metadata, discussion history, merge status, and inline suggestions
- **Phase 1.5** — asks review mode: Full (worktree + tests + linter + architecture) or Quick (diff-only)
- **Phase 2** — sets up worktree and launches a subagent for deep analysis
- **Phase 3-4** — presents findings, resolves open design questions
- **Phase 5** — drafts review comment using `/review:writing-style`, posts as formal review
- **Post-approve** — recommends merge strategy (rebase vs squash vs merge)

Uses `gh` CLI for all GitHub operations and git worktrees to avoid disrupting the current checkout.

**git-review** — interactive annotation-based code review. Generates a cleaned-up diff, opens it in `$EDITOR` via agterm overlay, tmux popup, kitty overlay, or wezterm split-pane (agterm tried first). You annotate directly in the diff, and the script returns your changes as a git diff. Claude reads annotations, fixes code, regenerates the diff, and loops until you close the editor without changes. Supports auto-detection of uncommitted changes or branch diffs. **Agterm users**: needs `agtermctl` on PATH (bundled with agterm), no extra config; pane-scoped overlays need agterm 0.20.0+.

Run tests: `python3 plugins/review/skills/git-review/scripts/git-review.py --test`

**writing-style** — enforces direct, brief writing for tickets, PRs, code reviews, and commit messages. Core principles: brevity, honest feedback, problem-solution structure, technical precision, anti-AI-speak. Does NOT apply to README.md, public docs, or blog posts.

### planning

Structured implementation planning with interactive annotation review and autonomous plan execution.

| Component | Trigger | Description |
|-----------|---------|-------------|
| command | `/planning:make <desc>` | Structured implementation plan with interactive review loop |
| skill | `/planning:exec [plan-file]` | Autonomous plan executor — task loop, multi-phase review, optional finalize |
| hook | `PreToolUse` / CLI | Plan annotation in `$EDITOR` with diff-based feedback loop |
| agent | `plan-review` | Automated plan quality review — completeness, over-engineering, testing |
| agent | `external-plan-review` | Sends a plan to the external review tool (codex by default) before implementation |

**plan command** — creates a plan file in `docs/plans/yyyymmdd-<task-name>.md` through interactive context gathering:
- **Step 0** — parses intent and explores codebase for relevant context
- **Step 1** — asks focused questions one at a time (goal, scope, constraints, testing approach, title)
- **Step 1.5** — proposes 2-3 implementation approaches with trade-offs (skipped if obvious)
- **Step 2** — creates the plan file with tasks, file lists, test requirements, and progress tracking
- **Step 3** — offers interactive review (opens plan in `$EDITOR` via plan-annotate), auto review (plan-review agent or external reviewer), start implementation, or done

**plan-annotate.py** — interactive plan annotation tool. Opens plans in your `$EDITOR` via a terminal overlay (agterm overlay, tmux popup, kitty overlay, or wezterm split-pane), lets you annotate directly, and feeds a unified diff back to Claude so it revises the plan. Two modes:

- *Hook mode* (default) — intercepts `ExitPlanMode`, opens plan in editor, denies tool call with diff if changes made, forcing revision loop
- *File mode* (`plan-annotate.py <plan-file>`) — outputs unified diff to stdout for integration with custom workflows

Requirements: agterm, tmux, kitty, or wezterm terminal (agterm tried first), `$EDITOR` (defaults to `vi`). **Agterm users**: needs `agtermctl` on PATH (bundled with agterm), no extra config; pane-scoped overlays need agterm 0.20.0+. **Kitty users** must enable remote control in `kitty.conf`:

```
allow_remote_control yes
listen_on unix:/tmp/kitty-$KITTY_PID
```

*Note*: when `revdiff` is installed, the `ExitPlanMode` hook and `/planning:make` interactive review both route through `launch-plan-review.sh` instead, which supports a wider set of overlays: agterm, tmux, zellij, herdr, orca, kitty, wezterm/kaku, cmux, ghostty, iTerm2, and emacs vterm. The 4-terminal list above applies only to the `$EDITOR` fallback when revdiff is not installed.

*Disabling review*: set `PLANNING_DISABLE_REVDIFF=1` to skip interactive plan review entirely on both routes (revdiff and the `$EDITOR` fallback). No overlay opens and the plan proceeds to the normal `ExitPlanMode` confirmation. This exists for remote clients (`claude /remote-control`): the overlay always opens on the host terminal, which a mobile or web client cannot see or interact with, so review would otherwise block the session. The variable is read when review fires, so export it in your shell before starting a session you may later drive remotely.

The overlay popup size is configurable via env vars:

| Env var | Description | Default |
|---------|-------------|---------|
| `REVDIFF_POPUP_WIDTH` | Tmux/Zellij popup width (e.g., `100%`, `80%`) | `90%` |
| `REVDIFF_POPUP_HEIGHT` | Tmux/Zellij popup height / wezterm split percent | `90%` |

Run tests: `python3 plugins/planning/scripts/plan-annotate.py --test`

**plan-review agent** — automated plan quality reviewer. Analyzes plans for problem definition, solution correctness, scope creep, over-engineering, testing requirements, task granularity, and convention adherence. Used by the plan command's "Auto review" option. Outputs a structured report with severity-rated findings and an APPROVE/NEEDS REVISION verdict.

**external-plan-review agent** — the other choice under "Auto review". Sends the plan to the external review tool through `run-external-review.sh` (the configured `external_review_cmd`, or codex when unset), so design problems surface before any code exists. The reviewer reads the plan, the project's CLAUDE.md, the code the plan names and the custom planning rules, and reports wrong assumptions, missing steps, over-engineering and ordering problems. One pass: the plan command shows each finding with its own assessment, asks which to apply, and revises the plan for those. A reviewer that is not installed, fails, times out (10 minutes) or prints nothing is reported as such, never as a clean review.

**exec skill** — autonomous plan executor. Takes a plan file (from `/planning:make`) and executes it task-by-task using isolated subagents. Execution phases:

1. **Task loop** — one subagent per task section, commits after each, retries on failure
2. **Comprehensive review** — 5 parallel agents (quality, implementation, testing, simplification, documentation) + fixer
3. **Code smells** — smells agent checks conventions, CLAUDE.md rules, code style + fixer
4. **External review** — always runs through `run-external-review.sh`: the configured `external_review_cmd`, or `codex` when that is unset. Adversarial loop with severity-aware early exit (stops after the first iteration that finds no critical/major issues; minor findings are still fixed). A tool that is not installed makes the phase skip; a tool that runs and exits non-zero, or exits 0 with no output, is reported as a reviewer failure rather than a clean review
5. **Critical-only review** — 2 agents (quality + implementation), critical/major issues only + fixer
6. **Finalize** — rebase, squash, verify (optional)
7. **Stats summary** — single agent reads the session log + git state and reports total tokens / wall-clock / per-phase breakdown / branch churn / fixer iterations
8. **Completion** — moves the finished plan into a `completed/` subdirectory of its plans directory and commits the move (VCS-aware via `move-plan.sh`, no push), so completed plans leave the active plans directory and stop showing up as candidates on the next run; also reports every judgment call the run made on its own and any deviations from the plan

Review agents are read-only reporters. The fixer agent evaluates each finding, fixes confirmed issues, rejects false positives, and reports back.

**Autonomous by design** — the run assumes no human is available, so subagents never stop to ask questions. They resolve judgment calls the plan does not settle from the project's lint rules, CLAUDE.md, and surrounding code, log each decision and any plan deviation, and the orchestrator reports them all to you at completion. When the worktree option is chosen the entire run is isolated in a git worktree; the main working directory is never checked out to the feature branch or otherwise touched.

**VCS support** — the exec helper scripts are VCS-aware and work in both git and Mercurial (hg) repositories. The finalize and external-review phases remain git-only, but their behaviour can be customised for hg via `.claude/exec-plan/prompts/finalizer.md` and `.claude/exec-plan/prompts/codex-review.md` overrides.

**Customization** — prompts and agent definitions use a three-layer override chain (checked in order, first match wins):
1. Project: `.claude/exec-plan/prompts/` and `.claude/exec-plan/agents/`
2. User: `${CLAUDE_PLUGIN_DATA}/prompts/` and `${CLAUDE_PLUGIN_DATA}/agents/`
3. Bundled defaults (shipped with the plugin)

To customize, place your modified version in the override path. For example, to customize `prompts/review.md` at the project level:
```
.claude/exec-plan/prompts/review.md
```
Or at the user level (applies to all projects). To find `<plugin-id>`, run `ls ~/.claude/plugins/data/` and look for the planning plugin entry:
```
~/.claude/plugins/data/<plugin-id>/prompts/review.md
```
Same pattern works for any prompt or agent file — just mirror the path under the override directory.

Nothing is copied into the override directories automatically. Installs before planning 3.10.0 did seed the user-level directory with copies of every bundled prompt and agent — those copies still shadow the bundled defaults and no longer track upgrades, so check `~/.claude/plugins/data/<plugin-id>/` and delete anything you did not deliberately edit.

To start from the bundled version of a file, use the `customize-file.sh` helper, which copies it into place and prints the destination. `${CLAUDE_PLUGIN_ROOT}` and `${CLAUDE_PLUGIN_DATA}` only expand inside plugin-loaded skill files, so spell both paths out when running this yourself:
```bash
# paths for a marketplace install; adjust if you installed the plugin some other way,
# and confirm the data dir against `ls ~/.claude/plugins/data/`
PLUGIN_ROOT=~/.claude/plugins/marketplaces/umputun-cc-thingz/plugins/planning
PLUGIN_DATA=~/.claude/plugins/data/planning-umputun-cc-thingz

# project level, writes .claude/exec-plan/prompts/review.md
bash "$PLUGIN_ROOT/skills/exec/scripts/customize-file.sh" prompts/review.md

# user level, applies to all projects
bash "$PLUGIN_ROOT/skills/exec/scripts/customize-file.sh" prompts/review.md "$PLUGIN_DATA"
```
An override shadows the bundled default permanently and will not pick up changes from later plugin upgrades, so copy only the files you intend to edit. Delete the override to return to the bundled version.

Bundled prompts: `task.md`, `fixer.md`, `review.md`, `codex-review.md`, `finalizer.md`, `stats.md`, `progress-file.md`
Bundled agents: `quality.txt`, `implementation.txt`, `testing.txt`, `simplification.txt`, `documentation.txt`, `smells.txt`

**Customization patterns** — two common shapes:

- *Route the review fanout to named specialists.* Override `prompts/review.md` to launch named Claude Code subagents (`qa-expert`, `code-quality`, `go-test-expert`, `implementation-reviewer`, `documentation`) instead of generic `general-purpose`. The override controls the `subagent_type` for each parallel specialist.
- *Delegate to an existing skill.* Override a prompt or agent file to instruct the spawned subagent to read another skill's `SKILL.md` and follow its workflow. Examples: override `agents/smells.txt` to delegate to a `/smells` skill; override `prompts/finalizer.md` to delegate to a `/rebase-commits` skill. Useful when an installed skill captures the workflow better than the bundled default.

**Constraint** — subagents in current Claude Code do not have the Agent tool, so they cannot spawn other subagents. `prompts/review.md` is therefore read by the main session orchestrator directly (used as a playbook), not given to a subagent — that is how the 5-specialist fanout actually runs in parallel. Single-agent leaf work (`task.md`, `fixer.md`, `finalizer.md`, `codex-review.md`, `agents/smells.txt`) runs as a spawned subagent because no further fan-out is needed. Any custom override that needs to fan out must follow the same playbook pattern.

Configuration via `userConfig` (prompted at plugin install):

| Key | Default | Description |
|-----|---------|-------------|
| `external_review_cmd` | *(empty — falls back to codex)* | Command for the external review tool: code review in exec, plan review in make. See the contract below |
| `task_retries` | `1` | Retries for failed tasks before stopping |
| `review_iterations` | `5` | Max fix-and-recheck cycles during internal review |
| `external_review_iterations` | `10` | Max iterations for external review adversarial loop |
| `finalize_enabled` | `true` | Whether to run the finalize phase (rebase + squash) |
| `subagent_model` | *(empty — Claude Code's default subagent model)* | Model for all exec subagents: `opus`, `sonnet`, `haiku` or `fable`. Lets the orchestrator run on a different model than the subagents |
| `plans_dir` | `docs/plans` | Directory where plan files are located |

**External review contract** — review phase 3 and the external-plan-review agent both run through `run-external-review.sh`, which receives the `external_review_cmd` value and the resolved prompt. When the setting is empty it falls back to codex via `run-codex.sh`. A custom command must:

- be able to run shell commands and read files in the working tree — the code review prompt tells the reviewer to run a `git diff`, then read the plan file, the progress file, and source files for context; the plan review prompt tells it to read the plan, CLAUDE.md and the source files the plan names. A plain text-in/text-out LLM CLI satisfies every other bullet here and reviews nothing
- accept the prompt as its final argument (the command string may carry flags, for example `mytool review --strict`; arguments containing spaces are not supported, so wrap those in a script)
- write findings to stdout, one per line, tagged `CRITICAL`, `MAJOR`, or `MINOR`, and print `NO ISSUES FOUND` when clean
- sandbox itself — the reviewer must not modify the working tree, since fixes are applied by a separate fixer agent
- exit `0` even when it reports findings
- read nothing from stdin — the script redirects it from `/dev/null`, so a tool that waits for input would hang the run rather than review it

The configured value is shell-parsed before the script sees it — Claude Code substitutes it into the command line that launches `run-external-review.sh`. It lands inside single quotes, so the shell passes it through as one argument and `$`, backtick, `"` and `\` are inert, while spaces and `;` are safe; the split into command and flags is done by the script's own `read -ra`. Only a literal `'` cannot be expressed — wrap a command that needs one in a script and point the setting at that. Plugin config comes from user, flag, and policy settings only — never from project settings — so a checked-out repository cannot set this value.

Leaving the setting alone is supported and takes the codex fallback. Claude Code's skill-content substitution does not merge in the schema default the way the hook and MCP paths do: with no saved value it leaves the `${user_config.external_review_cmd}` reference in the skill text verbatim. The script recognises that literal token as "not configured" and falls back to codex, printing a note on stderr — so a plugin that was never taken through `/plugin configure` still runs review phase 3.

The script exits `127` when the configured command (or codex) is not on `PATH`, which makes the run skip the phase instead of treating it as a review failure. Both such messages carry a `run-external-review:` marker on stderr, and the run requires that marker before it treats a `127` as a skip — so a `127` raised by the reviewer itself (a wrapper script whose own inner tool is missing) is reported as a reviewer failure rather than silently skipping the review.

The prompt reaches the tool as a single argv element read from a file, not pasted into the command line, since it contains backticks that a shell would otherwise run as command substitutions.

Environment variables read by `run-codex.sh`:

| Variable | Default | Description |
|----------|---------|-------------|
| `CODEX_MODEL` | *(unset)* | Model name passed to `codex exec` via `-c model=...`. When unset, codex uses the model from `~/.codex/config.toml` |
| `CODEX_NO_OVERRIDES` | *(unset)* | When set to the literal value `1`, suppresses all `-c` overrides (`model`, `model_reasoning_effort`, `stream_idle_timeout_ms`). Useful for codex proxies / wrappers that reject `-c model/provider` overrides. Any other value (including `0`, `false`, empty) leaves the overrides on. |

### release-tools

Release workflow tools for creating versioned releases with auto-generated notes.

| Component | Trigger | Description |
|-----------|---------|-------------|
| skill | `/release-tools:new` | Create GitHub/GitLab/Gitea release with auto-versioning and release notes |
| skill | `/release-tools:last-tag` | Show commits since the last tag in a formatted table |

**release** — full release workflow: asks release type (hotfix/minor/major), auto-detects platform (GitHub/GitLab/Gitea), calculates semantic version, generates release notes grouped by type (features/improvements/fixes) from merged PRs and commits, updates CHANGELOG if present, shows preview for confirmation, then publishes. Includes helper scripts for platform detection, version calculation, and notes generation.

**last-tag** — shows commits since the last tag in a formatted table with date, author, hash, and description. Detects single vs multiple authors and adjusts table layout. Offers interactive drill-down into individual commit details.

### thinking-tools

Analytical thinking tools for objective analysis.

| Component | Trigger | Description |
|-----------|---------|-------------|
| skill | `/thinking-tools:ask-codex` | Consult OpenAI Codex for investigation, debugging, or code review |
| skill | `/thinking-tools:dialectic <statement>` | Prove and counter-prove a statement using parallel agents |
| skill | `/thinking-tools:root-cause-investigator` | Systematic 5-Why root cause analysis for errors and bugs |

**ask-codex** — consults OpenAI Codex as a second opinion for debugging, investigation, or code review. Uses the model from `~/.codex/config.toml`; set `CODEX_MODEL` to override it. Builds a focused prompt from conversation context, runs codex in read-only sandbox mode in the background, and presents findings with an independent assessment. Requires `codex` CLI to be installed and authenticated.

**dialectic** — runs two agents in parallel with opposing goals (thesis vs antithesis) to eliminate confirmation bias. One agent finds all positive evidence, the other finds all negative evidence. After both complete, synthesizes findings into an objective conclusion and verifies cited evidence against actual code.

Use cases: architecture decisions, bug analysis, performance claims, refactoring safety, code review.

**root-cause-investigator** — applies 5-Why methodology to drill from symptoms to fundamental root causes. Structures investigation through progressive depth: surface cause → process issues → system problems → design issues → root cause. Includes reference materials for common patterns (race conditions, resource exhaustion, integration failures) and investigation techniques.

### skill-eval

Forces skill evaluation before every response.

| Component | Trigger | Description |
|-----------|---------|-------------|
| hook | `UserPromptSubmit` | Forces skill evaluation before every response |

By default, Claude Code often ignores available skills and jumps straight to generic responses. This hook injects a system reminder on every prompt that enforces an evaluate → activate → implement sequence. When installed, Claude will either list relevant skills and call `Skill()` for each before implementing, or proceed directly when no skills are relevant.

### workflow

Session workflow helpers for knowledge capture, confusion handling, course correction, and clipboard operations, plus the repo's deferred-work backlog.

| Component | Trigger | Description |
|-----------|---------|-------------|
| skill | `/workflow:learn` | Capture strategic project knowledge to project CLAUDE.md (routes per-developer / per-checkout discoveries to CLAUDE.local.md when that file is present) |
| skill | `/workflow:clarify` | Investigate and explain user confusion, determine if real issue exists |
| skill | `/workflow:wrong` | Reset and re-evaluate when current approach isn't working |
| skill | `/workflow:md-copy` | Format final answer as markdown and copy to clipboard |
| skill | `/workflow:txt-copy` | Copy generated text content to clipboard |
| skill | `/workflow:backlog` | Read, work, and maintain deferred-work items in `docs/backlog/` |

**learn** — reviews conversation history, extracts strategic project knowledge (architecture patterns, conventions, operational insights), and saves selected items to the project CLAUDE.md. When `CLAUDE.local.md` is present, per-developer / per-checkout discoveries (machine-specific tooling, environment quirks) are routed there instead. Defers to any memory-placement guidance documented in the project or user `CLAUDE.md` or `.claude/rules/`. Uses granular selection via AskUserQuestion so the user picks exactly what to keep.

**clarify** — activates on confusion signals ("I don't understand", "why is this happening", etc.). Investigates the actual codebase to determine whether the confusion stems from a misunderstanding or a real issue. If real, proceeds to plan mode for a fix.

**wrong** — resets the current approach when it's not working. Re-analyzes the core problem, proposes 2-3 fresh alternatives with trade-offs, and recommends the best path forward.

**md-copy** — formats the session's final answer as clean markdown (bold titles instead of headings, proper tables, code blocks) and copies to clipboard. Cross-platform clipboard detection (macOS pbcopy, Linux xclip/xsel).

**txt-copy** — copies generated text (emails, messages, letters) to clipboard via a timestamped temp file. Cross-platform clipboard detection (macOS pbcopy, Linux xclip/xsel).

**backlog** — maintains `docs/backlog/`, one markdown file per deferred item, for work that is real but not being done now. Each item carries `worth` (yes/later/no) and `added` (ISO date) in frontmatter, plus `where` (path:line) when the item is anchored to one place, with a free body. Lists the backlog with each present `where` verified against the current tree so stale anchors are reported as stale rather than as work, takes a slug argument to jump straight to one item, and `--all` to walk every item to a disposition one at a time. Either form briefs the item first — summary, effort, blast radius, materiality — so the call is made against facts rather than the item's own account. Before appending it finds candidates by the `where` path and slug, settling it on the defect each one claims rather than on a shared path. No checkbox and no in-progress marker: the item is deleted in the commit that lands its fix. Refuses to write into a branch other than the repository default without asking first. Git only — the lifecycle is expressed in `git rm`, branch detection, and staging.

## Custom Rules

Both the **planning** and **brainstorm** plugins support custom rules injection — free-form markdown files loaded at skill invocation time and applied as additional instructions alongside built-in behavior.

**Two levels**, checked in order (first-found-wins, never merged):

1. **Project-level**: `.claude/<rules-file>.md` in the current working directory
2. **User-level**: `$CLAUDE_PLUGIN_DATA/<rules-file>.md` (per-plugin persistent storage)

When both non-empty files exist, only the project-level file is used. Empty files are treated as absent and fall through to the next level.

| Plugin | Rules file | Affects |
|--------|-----------|---------|
| planning | `planning-rules.md` | make, exec, plan-review |
| brainstorm | `brainstorm-rules.md` | brainstorm skill |

**Example** — create `.claude/planning-rules.md` in your project:

```markdown
## testing conventions
- use table-driven tests with testify
- mock external dependencies with moq
- aim for 80% coverage minimum

## plan structure preferences
- max 5 checkboxes per task
- always include rollback steps for migrations
```

**Managing rules** — ask the make command or brainstorm skill to add, show, or clear rules at either level (exec loads rules but management is done through make or brainstorm):

- "show my planning rules" — displays current rules and which level they came from
- "add Go testing rules to project-level planning rules" — writes to `.claude/planning-rules.md`
- "set up brainstorm rules from my-conventions.md" — reads file and writes to rules location
- "clear user-level brainstorm rules" — deletes `$CLAUDE_PLUGIN_DATA/brainstorm-rules.md`

## Credits

Some skills and scripts were influenced by or adapted from community ideas, blog posts, and open-source examples. Sources were not tracked accurately from the start. If you recognize your work and want proper attribution, please [open an issue](https://github.com/umputun/cc-thingz/issues) — I'll fix it.

## License

MIT
