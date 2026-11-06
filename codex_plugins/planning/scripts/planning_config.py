#!/usr/bin/env python3
"""Load Codex planning settings: defaults < user JSON < project JSON < env."""

import json
import os
from pathlib import Path


DEFAULTS = {
    "plans_dir": "docs/plans",
    "task_retries": 1,
    "review_iterations": 5,
    "external_review_iterations": 10,
    "external_review_timeout": 600,
    "external_review_provider": "deepseek",
    "external_review_model": "deepseek-flash",
    "opencode_command": ["opencode", "--standalone"],
    "finalize_enabled": True,
    "subagent_model": "",
}


def load_config(project: Path | None = None) -> dict:
    project = Path.cwd() if project is None else project
    user_home = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")
    config = dict(DEFAULTS)
    paths = (user_home / "planning.json", project / ".codex/planning.json")
    for path in dict.fromkeys(paths):
        if not path.is_file():
            continue
        try:
            values = json.loads(path.read_text())
        except (OSError, ValueError) as exc:
            raise ValueError(f"Cannot read {path}: {exc}") from exc
        if not isinstance(values, dict):
            raise ValueError(f"{path} must contain a JSON object")
        unknown = values.keys() - DEFAULTS.keys()
        if unknown:
            raise ValueError(f"Unknown settings in {path}: {', '.join(sorted(unknown))}")
        config.update(values)

    for key in ("external_review_provider", "external_review_model"):
        override = os.environ.get("PLANNING_" + key.upper())
        if override:
            config[key] = override

    for key in ("plans_dir", "external_review_provider", "external_review_model"):
        if not isinstance(config[key], str) or not config[key].strip():
            raise ValueError(f"{key} must be a non-empty string")
    if "/" in config["external_review_provider"]:
        raise ValueError("external_review_provider must be a provider ID without a slash")
    for key in ("task_retries", "review_iterations", "external_review_iterations", "external_review_timeout"):
        minimum = 0 if key == "task_retries" else 1
        if type(config[key]) is not int or config[key] < minimum:
            raise ValueError(f"{key} must be an integer >= {minimum}")
    if type(config["finalize_enabled"]) is not bool:
        raise ValueError("finalize_enabled must be a boolean")
    if not isinstance(config["subagent_model"], str):
        raise ValueError("subagent_model must be a string")
    config["subagent_model"] = config["subagent_model"].strip()
    command = config["opencode_command"]
    if not isinstance(command, list) or not command or any(
        not isinstance(arg, str) or not arg for arg in command
    ):
        raise ValueError("opencode_command must be a non-empty array of argument strings")
    return config


if __name__ == "__main__":
    import sys
    try:
        print(json.dumps(load_config(), indent=2))
    except ValueError as exc:
        print(f"planning config: {exc}", file=sys.stderr)
        sys.exit(1)
