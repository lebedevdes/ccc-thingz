# Settings, Rules, and Overrides

## Settings

`scripts/planning_config.py` merges settings by key in this order:

1. Built-in defaults.
2. `${CODEX_HOME:-$HOME/.codex}/planning.json` for the user.
3. `.codex/planning.json` in the project.
4. `PLANNING_EXTERNAL_REVIEW_PROVIDER` and `PLANNING_EXTERNAL_REVIEW_MODEL` environment overrides.

An absent file is fine. Invalid JSON, unknown settings, or incorrect value types are errors. No configuration is copied into the installed plugin. Respect the client's permissions when managing user or project configuration.

Example project or user settings:

```json
{
  "external_review_provider": "deepseek",
  "external_review_model": "deepseek-flash",
  "external_review_timeout": 600,
  "plans_dir": "docs/plans",
  "task_retries": 1,
  "review_iterations": 5,
  "external_review_iterations": 10,
  "finalize_enabled": true,
  "subagent_model": ""
}
```

All shown values are defaults. The default reviewer is DeepSeek V4.1 Flash via the direct DeepSeek provider. OpenCode's selector is `deepseek/deepseek-flash`; authentication and provider credentials belong to the user's OpenCode configuration. Configure another provider by its OpenCode ID and its model ID separately. Model IDs may include slashes, for example `anthropic/claude-sonnet-...` under a gateway provider; do not duplicate the provider prefix in the model field.

`opencode_command` defaults to `["opencode", "--standalone"]`. It is an argv array for an executable or wrapper, so paths/arguments containing spaces work without shell evaluation. The standalone flag applies the review process's inline permissions in a private OpenCode instance. OpenCode 2.2.5+ is required. Custom wrappers must support both `debug agents` (JSON effective agent permissions) and `run`. Permission discovery failures stop the review before any model request. The helper appends `run --format json --agent plan --model <provider>/<model> --file <attachment>` and the review instruction. Both plan and code review use the same provider/model settings; no fallback to Codex or another model occurs on failure.

## Subagent Model

`subagent_model` selects the model for every native subagent launched by `planning-exec`: task workers, review specialists, fixers, smells, finalizer, and stats. Set it in the same project or user `planning.json`; the project value takes precedence. A project value of `""` clears a user override. The value must be a string; surrounding whitespace is trimmed, and an empty value omits the launch override so the client's own defaults or inheritance apply.

Use a model ID supported by the current Codex client. The executor passes it as a native launch argument, using a fresh context where required (with `spawn_agent`, `fork_turns: "none"`). If the client cannot honor the selection, execution reports it without silently substituting a model. This setting does not change the main session's model or the external OpenCode reviewer; that reviewer uses `external_review_provider` and `external_review_model`. The thinking-tools configuration reader accepts the key because it shares this settings file.

## Custom Rules

Run `scripts/resolve-rules.sh planning-rules.md` from the project root. It reads the first non-empty file from:

1. `.codex/planning-rules.md`.
2. `${CODEX_HOME:-$HOME/.codex}/planning-rules.md`.

Rules supplement the skills and review criteria; they are never merged or embedded verbatim in a generated plan. To show rules, print the resolver output and identify which non-empty file supplied it. To add/update/clear rules, change only the requested rules file and preserve unrelated preferences. Ask for the level when it is unclear. Do not edit bundled files to store preferences.

## Prompt and Specialist Overrides

Resolve every reference through `scripts/resolve-file.sh <relative-path>`:

1. `.codex/exec-plan/<relative-path>`.
2. `${CODEX_HOME:-$HOME/.codex}/exec-plan/<relative-path>`.
3. Plugin `references/<relative-path>`.

An empty override is intentional and shadows the default. Overrides must remain valid for the role they replace. Use `scripts/customize-file.sh <relative-path>` for a project copy, or add the explicit user directory as the second argument for a user copy. The helper refuses overwrites and symlink traversal inside the override directory. Only copy files the user wants to customize: an override shadows subsequent bundled updates until the user removes it.

Examples: `prompts/task.md`, `prompts/fixer.md`, `prompts/plan-review.md`, `prompts/internal-plan-review.md`, `prompts/external-review.md`, `prompts/finalizer.md`, and `agents/quality.txt`. The internal plan-review prompt also uses `PLUGIN_ROOT` to locate the original template in `skills/planning-make/SKILL.md`. Plan-review overrides use `PLAN_FILE_PATH` and `USER_RULES`; code-review overrides also use `PROGRESS_FILE_PATH` and receive a diff attachment.
