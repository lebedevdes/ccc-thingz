# Planning configuration in OpenCode

This bundle targets OpenCode 2.2.5+. It preserves the Claude planning settings and workflow, with explicit JSON loading instead of Claude Code's `userConfig` interpolation.

## Settings

Run `python3 "<plugin-root>/scripts/planning_config.py"` from the active project root. Precedence is defaults, user settings, then project settings:

- User: `<OpenCode config directory>/planning.json`
- Project: `.opencode/planning.json`

The OpenCode config directory is `OPENCODE_CONFIG_DIR` when set, otherwise `${XDG_CONFIG_HOME:-$HOME/.config}/opencode`. Installing into a project does not change the location of user settings. `install.py --target` chooses an installation destination only; use `OPENCODE_CONFIG_DIR` if that destination is also your custom global config directory.

| Setting | Default | Meaning |
|---|---|---|
| `external_review_cmd` | `""` | Original whitespace-separated reviewer command and flags; empty uses Codex |
| `task_retries` | `1` | Fresh-child retries after the initial failed task attempt |
| `review_iterations` | `5` | Maximum phase-1 fix/recheck cycles |
| `external_review_iterations` | `10` | Maximum external review cycles |
| `finalize_enabled` | `true` | Rebase, organize commits and validate |
| `subagent_model` | `""` | Native child model override; empty preserves OpenCode defaults |

Plans always live in `docs/plans/`, with completed plans under `docs/plans/completed/`. This path is not configurable.

Example `.opencode/planning.json`:

```json
{
  "review_iterations": 3,
  "finalize_enabled": false
}
```

Set `subagent_model` to a model available in your OpenCode installation, in `provider/model` or `provider/model#variant` form. It applies to exec's tasks, reviewers, fixers, smells, finalizer and stats. It does not change the orchestrator or external reviewer. If the native tool cannot apply a requested override, the run reports that limitation instead of silently choosing another model. The two named plan-review agents can also be configured through OpenCode's own `agents` settings.

The loader rejects unknown settings and invalid values. Its JSON output includes `plugin_root` and `plugin_data_dir` for the orchestrator; these derived fields are not editable settings. `--get <setting>` prints a value for **quoted** shell substitution; never use its output with `eval`.

## Custom rules and prompt overrides

User data lives in `<OpenCode config directory>/planning/`, replacing Claude's per-plugin data directory. Rules use first-nonempty-file-wins:

1. `.opencode/planning-rules.md`
2. `<user-data>/planning-rules.md`

See [custom-rules.md](custom-rules.md). Prompt and specialist overrides use first-existing-file-wins:

1. `.opencode/exec-plan/<relative-path>`
2. `<user-data>/<relative-path>`
3. `skills/planning-exec/references/<relative-path>` in this bundle

Use `skills/planning-exec/scripts/resolve-file.sh` to read a prompt, and `customize-file.sh` to copy one for editing:

```bash
bash <plugin-root>/skills/planning-exec/scripts/customize-file.sh prompts/task.md
bash <plugin-root>/skills/planning-exec/scripts/customize-file.sh prompts/task.md <user-data>
```

Nothing is seeded automatically. An override shadows future bundled updates until removed. The copy helper refuses existing files, path traversal and symlinked project destination components. Keep overrides in the active worktree when using isolation. Existing `.claude` and `.codex` overrides are not loaded automatically; copy only those you deliberately want to port.

## External review

The original `skills/planning-exec/scripts/run-external-review.sh` contract is retained. A command receives the resolved prompt as its **last argument**, reads the active working tree without changing it, and returns findings on stdout tagged `CRITICAL`, `MAJOR` or `MINOR`, or `NO ISSUES FOUND`. stderr is separate and does not count as findings. Commands with arguments containing spaces need a wrapper script; the command string is split on whitespace, not evaluated as shell code.

With no command configured, `run-codex.sh` runs `codex exec --sandbox read-only`. It retains `CODEX_MODEL` and `CODEX_NO_OVERRIDES=1`; credentials and the default model remain in Codex's own configuration. A custom reviewer controls its own read-only mode.

The parent calls `python3 "<plugin-root>/scripts/run-review.py" "<prompt-file>"`. This adapter validates configuration and reads the prompt, then execs the original shell launcher with separate arguments. Configuration errors stop the launch; prompt text and command settings are never evaluated as shell source. Code reviews use a background OpenCode `shell` call with a ten-minute timeout; plan reviews use the same timeout in the foreground. Missing tools are skipped only for exit 127 with the launcher's `run-external-review:` stderr marker. Other failures, empty output, timeouts and malformed responses are reported explicitly. They never count as passed reviews.
