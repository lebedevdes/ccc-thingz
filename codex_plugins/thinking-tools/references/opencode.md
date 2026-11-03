# OpenCode Consultation

The plugin bundles its own transport and configuration reader; it does not require the planning plugin to be installed. Both plugins deliberately read the same settings:

1. Built-in defaults.
2. `${CODEX_HOME:-$HOME/.codex}/planning.json`.
3. `.codex/planning.json` in the active project/worktree, merged by key.
4. `PLANNING_EXTERNAL_REVIEW_PROVIDER` and `PLANNING_EXTERNAL_REVIEW_MODEL` overrides.

`subagent_model` is accepted in the shared settings file for compatibility with planning; it controls native `planning-exec` subagents and does not change the OpenCode consultation model.

Default settings relevant to consultation:

```json
{
  "external_review_provider": "deepseek",
  "external_review_model": "deepseek-flash",
  "external_review_timeout": 600,
  "opencode_command": ["opencode", "--standalone"]
}
```

The model selector is `<provider>/<model>`; the default identifies DeepSeek V4.1 Flash through the direct DeepSeek provider. Credentials stay in OpenCode's existing provider configuration. To change settings, edit the requested project or user file, preserving other keys and respecting the client's permissions. Do not modify plugin files or install a second planning plugin just to configure the model. Invalid JSON, unknown settings, or wrong value types are errors, consistent with planning.

## Run

From the active project/worktree root:

```text
python3 <plugin-root>/scripts/ask-opencode.py <prompt-file>
python3 <plugin-root>/scripts/ask-opencode.py <prompt-file> --mode review --diff-base <base-ref>
python3 <plugin-root>/scripts/ask-opencode.py <prompt-file> --attach <context-file> --attach <another-file>
```

Use quoted absolute paths. Optional context files are UTF-8 snapshots appended to the request, so an external plan or temporary log does not require access outside the project from OpenCode. `--diff-base` uses Git's merge base and includes committed fixes and tracked working changes, plus separate staged/unstaged diffs, Git status, and untracked paths for the reviewer to inspect. Omit that option for a focused file review or a non-Git investigation, and include the relevant files/data explicitly.

The helper invokes OpenCode's plan agent with a prompt attachment, native reading/search tools, and explicit denial of edits, shell, delegation, and questions. Standalone mode applies those inline permissions in a private OpenCode process. It inherits the user's provider configuration while adding the consultation permissions. The command must support `run --format json --agent plan --model <selector> --file <attachment>`, as in OpenCode 2.2.5.

Before requesting a model, the helper runs `debug agents` to resolve the plan agent's effective permissions, including defaults and global/project/inline restrictions. It narrows these to read/search operations only, converts `ask` to `deny` for noninteractive execution, and denies all other tools, including custom/MCP tools. It preserves provider settings and existing policies. Discovery failure aborts the review. OpenCode 2.2.5+ is required; wrappers must support both `debug agents` and `run`. Discovery and the model call share the configured timeout; SIGTERM, interruption, or timeout terminates the active process group.

## Results

The helper emits one JSON result to stdout:

| Status | Meaning | Exit |
|---|---|---|
| `completed` | Non-empty final assistant text in advice mode; includes `text` and `model` | 0 |
| `reviewed` | Valid structured review in review mode; includes `review` and `model` | 0 |
| `skipped` | Configured executable could not be found before launch | 127 |
| `failed` | Configuration/context/output error, reviewer failure, timeout, or interruption | nonzero |

Only the final assistant message counts. Thinking events, tool output, interim commentary, and stderr are not answers. Structured review validates its JSON contract, including the verdict/findings relationship. A present wrapper exiting 127 is a failure rather than a missing executable. Timeouts/interruption terminate the process group and discard partial answers. Do not infer success from silence or switch models/providers automatically.

When the client has a shorter shell-call limit, yield/resume the running process using its supported mechanism. Do not launch a second consultation for the same in-flight request. If access is rejected, report it and use the client's normal approval mechanism; do not bypass the restriction.
