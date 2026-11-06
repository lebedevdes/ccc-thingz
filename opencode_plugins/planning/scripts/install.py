#!/usr/bin/env python3
"""Install the planning bundle into native OpenCode 2 skills, commands and agents."""

import argparse
import json
import shutil
from pathlib import Path

from planning_config import config_dir


ROOT = Path(__file__).resolve().parent.parent
MARKER = "<!-- Installed by ccc-thingz planning for OpenCode. -->"
BUNDLE_RELATIVE = Path("skills") / "planning"
BUNDLE_MARKER = ".ccc-thingz-planning"
IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store")


def strip_frontmatter(text: str) -> str:
    if text.startswith("---\n"):
        end = text.find("\n---\n", 3)
        if end != -1:
            return text[end + 5:]
    return text


def generated_entries(target: Path):
    bundle_root = target / BUNDLE_RELATIVE
    workflow = strip_frontmatter((ROOT / "commands" / "make.md").read_text()).strip()
    yield target / "commands" / "planning:make.md", (
        "---\ndescription: Create structured implementation plan in docs/plans/\n"
        f"agent: build\nsubagent: false\n---\n\n{MARKER}\n\n"
        f"The installed planning bundle is {json.dumps(str(bundle_root))}. "
        "Use it as `PLUGIN_ROOT`; it is a prompt placeholder, not an environment variable supplied by OpenCode. "
        'Run `python3 "PLUGIN_ROOT/scripts/planning_config.py"` with `shell` from the active project root. '
        "Keep the returned settings and `plugin_data_dir` as `PLUGIN_DATA_DIR`. "
        "Substitute these paths in subsequent instructions before calling tools. Quote filesystem paths.\n\n"
        "Use OpenCode 2's `read`, `write`/`edit` (or `patch`), `glob`, `grep`, `shell`, `question` and `subagent` tools. "
        "Questions use `multiple`, not Claude Code's `multiSelect`. Reuse decisions the user already supplied. "
        "If this client cannot present a required question, ask in conversation and wait for the answer. "
        "Run this workflow in the main Build session, not OpenCode's restricted Plan agent: make writes the plan "
        "and its implementation choices require Build permissions. Run shell calls with the shell tool's `workdir` "
        "set to the active project root.\n\n"
        f"{workflow}\n\n"
        "The following text is the user's arguments, not shell code:\n\n$ARGUMENTS\n"
    )
    yield target / "commands" / "planning:exec.md", (
        f"---\ndescription: Execute a plan with reviews\nagent: build\nsubagent: false\n---\n\n{MARKER}\n\n"
        "Load the `planning-exec` skill and follow it in this main session.\n"
        "The following text is the user's arguments, not shell code:\n\n$ARGUMENTS\n"
    )
    for name in ("plan-review", "external-plan-review"):
        text = (ROOT / "agents" / f"{name}.md").read_text()
        header, body = text[4:].split("\n---\n", 1)
        yield target / "agents" / f"planning-{name}.md", (
            f"---\n{header}\n---\n\n{MARKER}\n\n"
            f"The installed planning bundle's PLUGIN_ROOT is {json.dumps(str(bundle_root))}.\n"
            "Use this absolute root if the parent did not supply one.\n" + body
        )


def install(target: Path, *, dry_run: bool = False) -> list[str]:
    bundle = target / BUNDLE_RELATIVE
    if ROOT == bundle or bundle in ROOT.parents:
        raise ValueError("Run install.py from the source checkout, not from the installed bundle")
    # Preflight every destination before writing anything, including dangling links.
    if bundle.exists() or bundle.is_symlink():
        if bundle.is_symlink() or not bundle.is_dir() or not (bundle / BUNDLE_MARKER).is_file():
            raise ValueError(f"Refusing to overwrite {bundle}; it is not this installer's planning bundle")
    entries = list(generated_entries(target))
    for destination, _ in entries:
        if destination.exists() or destination.is_symlink():
            if (destination.is_symlink() or not destination.is_file()
                    or MARKER not in destination.read_text()):
                raise ValueError(f"Refusing to overwrite {destination}; it is not this installer's generated file")

    output = [f"copy {bundle}"] + [f"write {destination}" for destination, _ in entries]
    if dry_run:
        return output
    if bundle.exists():
        shutil.rmtree(bundle)
    shutil.copytree(ROOT, bundle, ignore=IGNORE)
    (bundle / BUNDLE_MARKER).write_text("Managed by ccc-thingz planning install.py.\n")
    for destination, content in entries:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument("--project", type=Path, help="install under this project's .opencode directory")
    scope.add_argument("--target", type=Path, help="explicit OpenCode configuration directory")
    parser.add_argument("--update", action="store_true",
                        help="deprecated: re-running the installer always refreshes managed files")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    target = args.target if args.target is not None else (
        args.project / ".opencode" if args.project is not None else config_dir())
    try:
        messages = install(target.expanduser().resolve(), dry_run=args.dry_run)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"planning install: {exc}\n")
    print("\n".join(messages))


if __name__ == "__main__":
    main()
