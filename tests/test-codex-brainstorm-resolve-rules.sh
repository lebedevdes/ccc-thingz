#!/bin/bash
# Exercise the Codex rules resolver from a project outside the plugin checkout.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
RESOLVE_SCRIPT="$SCRIPT_DIR/../codex_plugins/brainstorm/skills/brainstorm/scripts/resolve-rules.sh"

python3 - "$RESOLVE_SCRIPT" <<'PY'
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

resolver = str(Path(sys.argv.pop()).resolve())


class RulesResolution(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="codex brainstorm ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = self.root / "project with spaces"
        (self.project / ".codex").mkdir(parents=True)
        self.user = self.root / "user with spaces"
        self.user.mkdir()
        self.env = {**os.environ, "CODEX_HOME": str(self.user)}

    def write(self, directory, content):
        (directory / "brainstorm-rules.md").write_text(content)

    def resolve(self, *args):
        return subprocess.run(
            ["bash", resolver, *args], cwd=self.project, env=self.env,
            check=True, capture_output=True, text=True,
        ).stdout

    def test_missing_rules(self):
        self.assertEqual(self.resolve("brainstorm-rules.md"), "")

    def test_project_rules(self):
        self.write(self.project / ".codex", "Project rules\n")
        self.assertEqual(self.resolve("brainstorm-rules.md"), "Project rules\n")

    def test_user_rules_from_codex_home(self):
        self.write(self.user, "User rules\n")
        self.assertEqual(self.resolve("brainstorm-rules.md"), "User rules\n")

    def test_project_wins_without_merging(self):
        self.write(self.project / ".codex", "Project rules\n")
        self.write(self.user, "User rules\n")
        self.assertEqual(self.resolve("brainstorm-rules.md"), "Project rules\n")

    def test_empty_project_falls_back_to_user(self):
        self.write(self.project / ".codex", "")
        self.write(self.user, "User rules\n")
        self.assertEqual(self.resolve("brainstorm-rules.md"), "User rules\n")

    def test_empty_files(self):
        self.write(self.project / ".codex", "")
        self.write(self.user, "")
        self.assertEqual(self.resolve("brainstorm-rules.md"), "")

    def test_directory_argument_overrides_codex_home(self):
        alternate = self.root / "alternate user"
        alternate.mkdir()
        self.write(alternate, "Explicit directory\n")
        self.write(self.user, "CODEX_HOME directory\n")
        self.assertEqual(
            self.resolve("brainstorm-rules.md", str(alternate)),
            "Explicit directory\n",
        )

    def test_missing_filename(self):
        self.assertEqual(self.resolve(), "")


unittest.main(verbosity=2)
PY
