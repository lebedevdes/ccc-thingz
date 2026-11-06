# Planning for OpenCode 2

Adapted directly from `plugins/planning` v3.12.0. The original `commands/make.md`, `skills/planning-exec/`, specialist prompts, shell helpers and annotation scripts keep their structure. This is a native skills/commands/agents bundle; `plugin.json` records this repository's version metadata, not an OpenCode runtime-plugin manifest. No JavaScript plugin or npm installation is required.

## Install

Requirements: OpenCode 2.2.5+, Python 3.10+, Bash, Git (or Mercurial for the supported phases). Codex is needed only for the default external reviewer. Optional interactive annotations use `revdiff`, or `$EDITOR`, in a supported terminal/multiplexer.

From the ccc-thingz checkout, install globally:

```bash
python3 opencode_plugins/planning/scripts/install.py
```

Or install into one project:

```bash
python3 opencode_plugins/planning/scripts/install.py --project /path/to/project
```

`--target /path/to/opencode-config` selects an explicit config directory. `--dry-run` previews changes. The installer preflights all destinations and refuses unrelated existing files. Re-running it overwrites the managed bundle and generated commands/agents. It never edits `opencode.json`, permissions, provider credentials or planning preferences.

It copies the whole bundle to `skills/planning/`, then writes:

- `commands/planning:make.md` → the full planning workflow, with the bundle root and settings loader supplied
- `commands/planning:exec.md` → a thin wrapper that loads the `planning-exec` skill
- `agents/planning-plan-review.md` and `agents/planning-external-plan-review.md` → native leaf-agent definitions with the bundle root supplied

The copied bundle is self-contained: the exec skill lives under `skills/planning/skills/planning-exec/`, the make workflow source under `commands/`, and shared `scripts/` and `references/` beside them. Make is a command only, matching the Claude source; there is no duplicate make skill. OpenCode discovers the nested `SKILL.md` file, so no symlinks and no configuration edit are needed. Re-run the installer after changing the source to refresh the copy. OpenCode reloads configuration, skills, commands and agents automatically; run `/reload` if a change is not picked up. Always install the agents with this installer: it decodes their `planning-` IDs from the filenames, so copying `agents/` by hand changes the IDs and makes `make` fall back to a plain `general` child.

To uninstall, remove `skills/planning/`, the two command files and the two agent files, retaining any user settings, rules and overrides. The source checkout and project plans are separate from the installed entries.

## Make

```text
/planning:make add caching to the API
```

The command runs the full planning workflow in the main Build session. It preserves discovery, one-question-at-a-time context gathering, approach selection, the complete plan template and next-step choices:

- Interactive review: the original revdiff/editor annotation loop.
- Auto review: internal `planning-plan-review` or the external reviewer, with findings selected by the user before revising the plan.
- Implement: commit only the plan, then choose interactive implementation or autonomous exec.
- Done: commit only the plan and stop.

Plans live in `docs/plans/` throughout. Both named review agents can also be invoked explicitly with an absolute plan path. If unavailable, make resolves the same bundled leaf prompt and uses a fresh `general` child.

## Exec

```text
/planning:exec docs/plans/20261104-api-cache.md
```

The command loads `planning-exec` in the **main session**, retaining the original thirteen steps:

1. Resolve the plan and default branch.
2. Choose current checkout or isolated worktree, unless already specified.
3. Create a visible task/stage list.
4. Create a branch (skipped if already created in the worktree).
5. Initialize the progress file.
6. Execute one Task/Iteration section per fresh child, strictly sequentially; re-read checkboxes and retry failures.
7. Comprehensive review: five parallel specialists; subsequent rounds use two critical/major reviewers and a separate fixer.
8. Code-smells review and fixer.
9. External adversarial review loop, Codex by default.
10. Final critical/major review and fixer.
11. Optional rebase, commit cleanup and validation.
12. Stats summary.
13. Report decisions/deviations and actual phase outcomes; move the completed plan and commit its move. Never push.

All exec children use `general` with resolved specialist prompts. Reviewers read in parallel; writers start only after all reviewers finish. OpenCode permission failures and review errors stay visible. A skipped/failed review never becomes “reviews passed”.

Worktrees are created directly from the current HEAD without switching the original checkout. The session is moved to the worktree through OpenCode's session utility before launching children, in a separate tool-call boundary. Only the selected uncommitted plan and required planning settings/overrides are carried; unrelated changes are preserved. With no session-move support, the user must resume in the worktree before execution continues.

## Configuration and customization

See [configuration.md](configuration.md) for the original seven settings, external-review contract and override locations, and [custom-rules.md](custom-rules.md) for rules management.

Original leaf prompts remain under `skills/planning-exec/references/prompts/`; the five review specialists plus smells remain under `skills/planning-exec/references/agents/`. `review.md` is still a parent-session playbook, never a child prompt. Overrides retain this same distinction.

## Differences from Claude Code

- `subagent`, `shell`, `question` and Code Mode replace Claude's tool calls and parallel tool-use syntax. No permission-bypass mode is requested.
- Paths/settings are loaded explicitly rather than interpolated from Claude plugin variables.
- The original `ExitPlanMode` hook is **not installed**: OpenCode has no compatible Claude `PreToolUse`/`ExitPlanMode` event. Explicit interactive review in make retains the annotation loop. The copied `plan-annotate.py` also retains its upstream hook mode for source parity, but OpenCode invokes only its file mode.
- Task/stage tracking uses the conversation/progress file unless a client exposes a native task-list tool.
- Stats use available OpenCode metrics; unavailable token/tool/timing measurements are `n/a`, rather than guessed or read from Claude logs.
- The original Git/Hg boundary is retained: worktrees, external code review and finalization are skipped on Hg. Merely overriding a prompt does not change these skip conditions.

Sources: [OpenCode 2 skills](https://opencode.ai/v2/docs/skills/), [commands](https://opencode.ai/v2/docs/commands/), [agents](https://opencode.ai/v2/docs/agents/), [tools](https://opencode.ai/v2/docs/tools/).

## Validation

```bash
bash tests/test-opencode-planning.sh
python3 .github/scripts/check-frontmatter.py opencode_plugins
```

The tests use temporary projects and fake reviewers. They do not call models or install into the user's actual OpenCode configuration. Run the optional native checks with:

```bash
OPENCODE_PLANNING_LIVE=1 python3 tests/opencode-planning-tests.py PlanningTests.test_native_discovery PlanningTests.test_native_skill_and_command_registration
```

These start isolated OpenCode servers and check agents, skills and namespaced commands, without model calls. The registration check waits for asynchronous catalog loading. Full model-driven plan execution requires a configured provider and an interactive OpenCode client.
