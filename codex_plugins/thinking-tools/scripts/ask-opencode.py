#!/usr/bin/env python3
"""Ask OpenCode for read-only advice or a validated structured review."""

import argparse
import json
from pathlib import Path
import signal
import subprocess
import sys

from opencode_client import ConsultationError, run_query


def parse_review(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) >= 3 and lines[0].lower() in ("```", "```json") and lines[-1] == "```":
            text = "\n".join(lines[1:-1])
    try:
        value = json.loads(text)
    except ValueError as exc:
        raise ConsultationError("Review output is not valid JSON") from exc
    if not isinstance(value, dict) or value.get("verdict") not in ("approve", "needs-attention"):
        raise ConsultationError("Review must contain an approve or needs-attention verdict")
    if not isinstance(value.get("summary"), str) or not value["summary"].strip():
        raise ConsultationError("Review must contain a non-empty summary")
    findings = value.get("findings")
    if not isinstance(findings, list):
        raise ConsultationError("Review findings must be an array")
    for finding in findings:
        if not isinstance(finding, dict):
            raise ConsultationError("Each review finding must be an object")
        if finding.get("severity") not in ("critical", "high", "medium", "low"):
            raise ConsultationError("Invalid review severity")
        for key in ("title", "body", "file", "recommendation"):
            if not isinstance(finding.get(key), str) or not finding[key].strip():
                raise ConsultationError(f"Finding requires non-empty {key}")
        start, end = finding.get("line_start"), finding.get("line_end")
        if type(start) is not int or type(end) is not int or start < 1 or end < start:
            raise ConsultationError("Finding line range must be positive and ordered")
        confidence = finding.get("confidence")
        if type(confidence) not in (int, float) or not 0 <= confidence <= 1:
            raise ConsultationError("Finding confidence must be a number from 0 to 1")
    steps = value.get("next_steps")
    if not isinstance(steps, list) or any(not isinstance(step, str) or not step.strip() for step in steps):
        raise ConsultationError("Review next_steps must be an array of non-empty strings")
    if (value["verdict"] == "approve") != (not findings):
        raise ConsultationError("Review verdict contradicts its findings")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prompt_file", type=Path)
    parser.add_argument("--mode", choices=("advice", "review"), default="advice")
    parser.add_argument("--diff-base", help="Attach the full Git change from the merge base")
    parser.add_argument("--attach", type=Path, action="append", default=[], help="Attach a selected context file; repeatable")
    args = parser.parse_args()
    try:
        contract = ""
        if args.mode == "review":
            contract = (Path(__file__).resolve().parents[1] / "references/review-contract.md").read_text()
        result, code = run_query(args.prompt_file, args.diff_base, args.attach, contract)
        if code == 0 and args.mode == "review":
            result = {"status": "reviewed", "review": parse_review(result["text"]), "model": result["model"]}
    except KeyboardInterrupt:
        result, code = {"status": "failed", "error": "OpenCode consultation interrupted"}, 130
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        result, code = {"status": "failed", "error": str(exc)}, 1
    print(json.dumps(result, ensure_ascii=False))
    return code


if __name__ == "__main__":
    def interrupt(signum, frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, interrupt)
    sys.exit(main())
