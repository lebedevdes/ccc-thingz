#!/usr/bin/env python3
"""Bundled OpenCode transport for read-only consultation and structured review."""

import json
from pathlib import Path
import subprocess
import tempfile
import time

from opencode_runtime import readonly_environment, run_command

from opencode_config import load_config


class ConsultationError(ValueError):
    pass


def response_text(output: str) -> str:
    """Keep assistant text only; tool output and thinking are not answers."""
    messages: dict[str, list[str]] = {}
    for line in output.splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except ValueError as exc:
            raise ConsultationError("OpenCode emitted invalid JSON") from exc
        if not isinstance(event, dict):
            raise ConsultationError("OpenCode emitted a non-object event")
        if event.get("type") == "error":
            raise ConsultationError("OpenCode error: " + json.dumps(event.get("error", event), ensure_ascii=False))
        part = event.get("part") or {}
        if event.get("type") == "text" and isinstance(part, dict):
            text = part.get("text")
            if isinstance(text, str):
                key = str(part.get("messageID", "response"))
                messages.setdefault(key, []).append(text)
    if not messages:
        raise ConsultationError("OpenCode returned no assistant text")
    # A consultation may have interim commentary before tool calls. Use the last
    # assistant message, not echoed prompts, tool results, or earlier commentary.
    return "\n".join(next(reversed(messages.values()))).strip()


def consultation_environment(config) -> dict:
    return readonly_environment(config["opencode_command"], config["external_review_timeout"])


def code_diff(base: str) -> str:
    def git(*args):
        return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout
    merge_base = git("merge-base", base, "HEAD").strip()
    # Include committed fixes and tracked uncommitted changes on every iteration.
    diff = git("diff", "--no-ext-diff", "--no-textconv", merge_base, "--")
    staged = git("diff", "--no-ext-diff", "--no-textconv", "--cached", "HEAD", "--")
    unstaged = git("diff", "--no-ext-diff", "--no-textconv", "--")
    status = git("status", "--short", "--untracked-files=all")
    untracked = git("ls-files", "--others", "--exclude-standard")
    return (f"\n\n## Code diff from merge base to working tree\n```diff\n{diff}\n```"
            f"\n\n## Staged diff (HEAD to index)\n```diff\n{staged}\n```"
            f"\n\n## Unstaged diff (index to working tree)\n```diff\n{unstaged}\n```"
            f"\n\n## Git status\n```text\n{status}\n```"
            f"\n\nUntracked paths (inspect with read tools):\n{untracked or '(none)'}")


def run_query(prompt_file: Path, base: str | None = None, attachments: list[Path] | None = None,
              instructions: str = "") -> tuple[dict, int]:
    config = load_config()
    prompt = prompt_file.read_text()
    if not prompt.strip():
        raise ConsultationError("Consultation prompt file is empty")
    if instructions:
        prompt += "\n\n" + instructions
    for path in attachments or []:
        prompt += f"\n\n## Context snapshot: {path}\n{path.read_text()}"
    if base:
        prompt += code_diff(base)
    selector = config["external_review_provider"] + "/" + config["external_review_model"]
    with tempfile.TemporaryDirectory(prefix="opencode-consultation-") as temporary:
        attachment = Path(temporary) / "review.md"
        attachment.write_text(prompt)
        command = [*config["opencode_command"], "run", "--format", "json", "--agent", "plan",
                   "--model", selector, "--file", str(attachment),
                   "Answer the attached consultation request using repository evidence and attached context. Do not modify files or ask questions. Follow its requested output format."]
        try:
            deadline = time.monotonic() + config["external_review_timeout"]
            env = consultation_environment(config)
            stdout, stderr, returncode = run_command(command, env, max(0, deadline - time.monotonic()))
        except FileNotFoundError:
            return {"status": "skipped", "error": f"OpenCode executable not found: {command[0]}"}, 127
        except (subprocess.TimeoutExpired, KeyboardInterrupt) as exc:
            reason = "timed out" if isinstance(exc, subprocess.TimeoutExpired) else "interrupted"
            return {"status": "failed", "error": f"OpenCode consultation {reason}; partial output discarded"}, 124
    if returncode:
        detail = stderr.strip().splitlines()[-1:] or stdout.strip().splitlines()[-1:]
        return {"status": "failed", "error": f"OpenCode exited {returncode}: {' '.join(detail)}"}, 1
    text = response_text(stdout)
    if not text:
        raise ConsultationError("OpenCode returned an empty final answer")
    return {"status": "completed", "text": text, "model": selector}, 0
