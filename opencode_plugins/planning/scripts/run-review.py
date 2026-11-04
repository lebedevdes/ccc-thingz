#!/usr/bin/env python3
"""Pass a prompt file and loaded settings to the original external-review launcher."""

import argparse
import os
from pathlib import Path

from planning_config import load_config


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prompt_file", type=Path)
    args = parser.parse_args()
    try:
        settings = load_config()
        prompt = args.prompt_file.read_text()
        if not prompt.strip():
            raise ValueError("review prompt is empty")
        launcher = Path(__file__).resolve().parent.parent / "skills/planning-exec/scripts/run-external-review.sh"
        # exec preserves exit codes, stdout/stderr separation and cancellation of
        # the original exec chain. Neither settings nor prompt text becomes code.
        os.execvp("bash", ["bash", str(launcher), settings["external_review_cmd"], prompt])
    except (OSError, ValueError) as exc:
        parser.exit(1, f"planning review: {exc}\n")


if __name__ == "__main__":
    main()
