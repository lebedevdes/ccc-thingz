#!/usr/bin/env python3
"""Claude planning userConfig equivalents for OpenCode: defaults < user < project."""

import argparse
import json
import os
from pathlib import Path


DEFAULTS = {
    "external_review_cmd": "",
    "task_retries": 1,
    "review_iterations": 5,
    "external_review_iterations": 10,
    "finalize_enabled": True,
    "subagent_model": "",
}


def config_dir() -> Path:
    override = os.environ.get("OPENCODE_CONFIG_DIR")
    if override:
        return Path(override).expanduser().resolve()
    base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return (base / "opencode").expanduser().resolve()


def load_config(project: Path | None = None) -> dict:
    project = Path.cwd() if project is None else project
    settings = dict(DEFAULTS)
    for path in dict.fromkeys((config_dir() / "planning.json", project / ".opencode/planning.json")):
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
        settings.update(values)
    for key in ("task_retries", "review_iterations", "external_review_iterations"):
        minimum = 0 if key == "task_retries" else 1
        if type(settings[key]) is not int or settings[key] < minimum:
            raise ValueError(f"{key} must be an integer >= {minimum}")
    if type(settings["finalize_enabled"]) is not bool:
        raise ValueError("finalize_enabled must be a boolean")
    for key in ("external_review_cmd", "subagent_model"):
        if not isinstance(settings[key], str):
            raise ValueError(f"{key} must be a string")
    settings["subagent_model"] = settings["subagent_model"].strip()
    if "\n" in settings["external_review_cmd"]:
        raise ValueError("external_review_cmd must be a single line")
    model = settings["subagent_model"]
    if model and ("/" not in model or not all(model.split("/", 1)) or any(c.isspace() for c in model)):
        raise ValueError("subagent_model must use OpenCode's provider/model format (optional #variant)")
    return settings


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--get", choices=DEFAULTS, help="print one setting as data, for quoted shell substitution")
    args = parser.parse_args()
    try:
        settings = load_config()
        if args.get:
            value = settings[args.get]
            print(value if isinstance(value, str) else json.dumps(value))
        else:
            print(json.dumps({**settings,
                             "plugin_root": str(Path(__file__).resolve().parent.parent),
                             "plugin_data_dir": str(config_dir() / "planning")}, indent=2))
    except (OSError, ValueError) as exc:
        parser.exit(1, f"planning config: {exc}\n")


if __name__ == "__main__":
    main()
