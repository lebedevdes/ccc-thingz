#!/usr/bin/env python3
"""Run an OpenCode review and emit a JSON result. Never infer clean from silence."""

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

from opencode_runtime import readonly_environment, run_command

from planning_config import load_config


class ReviewError(ValueError):
    pass


def review_text(output: str) -> str:
    """Keep assistant text only; tool output and thinking are not findings."""
    messages: dict[str, list[str]] = {}
    for line in output.splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except ValueError as exc:
            raise ReviewError("OpenCode emitted invalid JSON") from exc
        if not isinstance(event, dict):
            raise ReviewError("OpenCode emitted a non-object event")
        if event.get("type") == "error":
            raise ReviewError("OpenCode error: " + json.dumps(event.get("error", event), ensure_ascii=False))
        part = event.get("part") or {}
        if event.get("type") == "text" and isinstance(part, dict):
            text = part.get("text")
            if isinstance(text, str):
                key = str(part.get("messageID", "response"))
                messages.setdefault(key, []).append(text)
    if not messages:
        raise ReviewError("OpenCode returned no assistant text")
    # A review may have interim commentary before tool calls. Only judge the last
    # assistant message, not echoed prompts, tool results, or earlier commentary.
    return "\n".join(next(reversed(messages.values()))).strip()


def classify(text: str) -> dict:
    # Anchor tags to finding lines, so prose mentioning severity is not a finding.
    tags = re.findall(r"^\s*(?:[-*]\s+|\d+[.)]\s+)?(?:\*\*|`)?(CRITICAL|MAJOR|MINOR)\s*:", text, re.I | re.M)
    if tags:
        return {"status": "findings", "text": text, "has_blocking": any(t.upper() in ("CRITICAL", "MAJOR") for t in tags)}
    if re.fullmatch(r"NO ISSUES FOUND\.?", text.strip(), re.I):
        return {"status": "clean", "text": text, "has_blocking": False}
    raise ReviewError("No severity-tagged findings and no clean marker in the final answer")


def review_environment(config) -> dict:
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


def run_review(prompt_file: Path, base: str | None, plan_file: Path | None = None,
               progress_file: Path | None = None) -> tuple[dict, int]:
    config = load_config()
    prompt = prompt_file.read_text()
    if not prompt.strip():
        raise ReviewError("Review prompt file is empty")
    for title, path in (("Plan snapshot", plan_file), ("Progress snapshot", progress_file)):
        if path is not None:
            prompt += f"\n\n## {title}: {path}\n{path.read_text()}"
    if base:
        prompt += code_diff(base)
    selector = config["external_review_provider"] + "/" + config["external_review_model"]
    with tempfile.TemporaryDirectory(prefix="planning-review-") as temporary:
        attachment = Path(temporary) / "review.md"
        attachment.write_text(prompt)
        command = [*config["opencode_command"], "run", "--format", "json", "--agent", "plan",
                   "--model", selector, "--file", str(attachment),
                   "Review the attached instructions and repository sources. Do not modify files or ask questions. Return only severity-tagged findings, or exactly NO ISSUES FOUND."]
        try:
            deadline = time.monotonic() + config["external_review_timeout"]
            env = review_environment(config)
            stdout, stderr, returncode = run_command(command, env, max(0, deadline - time.monotonic()))
        except FileNotFoundError:
            return {"status": "skipped", "error": f"OpenCode executable not found: {command[0]}"}, 127
        except (subprocess.TimeoutExpired, KeyboardInterrupt) as exc:
            reason = "timed out" if isinstance(exc, subprocess.TimeoutExpired) else "interrupted"
            return {"status": "failed", "error": f"OpenCode review {reason}; partial output discarded"}, 124
    if returncode:
        detail = stderr.strip().splitlines()[-1:] or stdout.strip().splitlines()[-1:]
        return {"status": "failed", "error": f"OpenCode exited {returncode}: {' '.join(detail)}"}, 1
    return {**classify(review_text(stdout)), "model": selector}, 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prompt_file", type=Path)
    parser.add_argument("--diff-base", help="Attach the complete Git branch diff, including tracked working changes")
    parser.add_argument("--plan-file", type=Path, help="Attach the plan, including plans outside the repository")
    parser.add_argument("--progress-file", type=Path, help="Attach prior findings/fixes from the temporary progress log")
    args = parser.parse_args()
    try:
        result, code = run_review(args.prompt_file, args.diff_base, args.plan_file, args.progress_file)
    except KeyboardInterrupt:
        result, code = {"status": "failed", "error": "OpenCode review interrupted"}, 130
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        result, code = {"status": "failed", "error": str(exc)}, 1
    print(json.dumps(result, ensure_ascii=False))
    return code


if __name__ == "__main__":
    import signal

    def interrupt(signum, frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, interrupt)
    sys.exit(main())
