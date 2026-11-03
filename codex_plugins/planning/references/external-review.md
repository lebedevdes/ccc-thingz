# External Review Through OpenCode

Use the same runner for plan and code review. Settings are loaded by `scripts/planning_config.py`; provider and model default to `deepseek` and `deepseek-flash` (DeepSeek V4.1 Flash).

## Invocation

Resolve `prompts/plan-review.md` for a plan or `prompts/external-review.md` for code through `scripts/resolve-file.sh`. Substitute the absolute plan/progress paths and custom rules. Write the resolved prompt to a file in the run's unique temporary directory with a file-writing tool or a safely quoted program. Do not interpolate prompt text into shell commands.

From the active project/worktree root, run:

```text
python3 <plugin-root>/scripts/run-external-review.py <prompt-file> --plan-file <plan-file>
python3 <plugin-root>/scripts/run-external-review.py <prompt-file> --plan-file <plan-file> --progress-file <progress-file> --diff-base <default-branch>
```

The first command reviews a plan. The second reviews code and appends a snapshot of the entire Git change from the merge base to the current working tree, including committed fixes and tracked uncommitted changes, plus separate staged/unstaged diffs, Git status, and untracked paths to inspect. Use it on every iteration, not just the first one. The plan and prior findings/fixes are attached as snapshots too, so a plan or progress log outside the repository does not require external-directory access from the reviewer.

The runner sends the prompt/snapshot as a file attachment and explicitly selects `<provider>/<model>`. OpenCode runs in its plan agent with native reading/search tools; shell, editing, delegation, and questions are disabled for this review process. It reports findings; Codex applies fixes. Existing inline provider configuration is preserved when adding the review permissions. No credentials are written by the plugin.

The helper waits up to `external_review_timeout` seconds and terminates the process group on timeout/interruption, discarding partial findings. If the client has a shorter tool-call limit, use its supported yielding/background execution and resume it; do not launch duplicate reviews. Do not retry automatically after a permission rejection.

Before requesting a model, the helper runs `debug agents` to resolve the plan agent's effective permissions, including defaults and global/project/inline restrictions. It narrows these to read/search operations only, converts `ask` to `deny` for noninteractive execution, and denies all other tools, including custom/MCP tools. It preserves provider settings and existing policies. Discovery failure aborts the review. OpenCode 2.2.5+ is required; wrappers must support both `debug agents` and `run`. Discovery and the model call share the configured timeout; SIGTERM, interruption, or timeout terminates the active process group.

## Results

Stdout is one JSON object. Judge the object rather than scanning process logs:

| `status` | Meaning | Exit |
|---|---|---|
| `clean` | Final assistant answer is exactly `NO ISSUES FOUND` (optional final period) | 0 |
| `findings` | Final assistant answer has severity-tagged finding lines; includes full `text` and `has_blocking` | 0 |
| `skipped` | Configured OpenCode executable is missing | 127 |
| `failed` | Invalid config/prompt/output, tool/auth/model failure, nonzero reviewer exit, timeout, interruption, or empty answer | nonzero |

Only final assistant text events count. Thinking, tool output, earlier assistant commentary, and stderr do not become findings. Tagged findings take precedence over an incidental clean marker. Unstructured prose without finding tags or the exact clean marker is a failed review. A present wrapper returning 127 is a failure, distinct from an executable missing before launch.

For a plan review, show each finding with the parent's assessment and ask which to apply unless already authorized. For code execution, pass the complete findings text to the fixer. Re-review after blocking findings; fix a minor-only result once, then continue to the final internal critical review. Record errors, skipped phases, and exhausted limits accurately. Do not silently replace a failing reviewer or declare all reviews passed.
