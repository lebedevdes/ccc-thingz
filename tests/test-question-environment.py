import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "codex_plugins/planning/skills/planning-make/scripts/question-environment.sh"


class QuestionEnvironmentTest(unittest.TestCase):
    def run_script(self, env):
        result = subprocess.run(["/bin/sh", str(SCRIPT)], env=env, text=True,
                                capture_output=True, check=True)
        return json.loads(result.stdout)

    def test_no_agterm(self):
        result = self.run_script({"PATH": "/usr/bin:/bin"})
        self.assertEqual(result["agterm_picker"], "unavailable")
        self.assertIn("unknown", result["client_question_tools"])
        self.assertIsNone(result["environment"]["AGTERM_SESSION_ID"])

    def test_environment_identifies_current_window(self):
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "agtermctl"
            executable.write_text("#!/bin/sh\nexit 1\n")
            executable.chmod(0o755)
            env = {"PATH": directory + ":/usr/bin:/bin", "AGTERM_ENABLED": "1", "AGTERM_SESSION_ID": "session",
                   "AGTERM_WINDOW_ID": "window", "AGTERM_SOCKET": "/some/socket"}
            result = self.run_script(env)
            self.assertEqual(result["environment"]["AGTERM_SESSION_ID"], "session")
            self.assertEqual(result["environment"]["AGTERM_WINDOW_ID"], "window")
            self.assertEqual(result["environment"]["AGTERM_SOCKET"], "/some/socket")
            self.assertEqual(result["agterm_picker"], "candidate")

    def test_json_escapes_environment_values(self):
        socket = '/tmp/"socket"\\with\nnewline\tand control\x01\n'
        result = self.run_script({"PATH": "/usr/bin:/bin", "AGTERM_SOCKET": socket})
        self.assertEqual(result["environment"]["AGTERM_SOCKET"], socket)

    def test_missing_window_is_unavailable(self):
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "agtermctl"
            executable.touch(mode=0o755)
            env = {"PATH": directory + ":/usr/bin:/bin", "AGTERM_ENABLED": "1", "AGTERM_SESSION_ID": "session"}
            result = self.run_script(env)
            self.assertEqual(result["agterm_picker"], "unavailable")

    def test_bundled_copies_match(self):
        skills = [p for p in (ROOT / "codex_plugins").glob("*/skills/*/SKILL.md")
                  if "## Questions in Codex" in p.read_text()]
        self.assertTrue(skills)
        for skill in skills:
            with self.subTest(skill=skill):
                self.assertEqual((skill.parent / "scripts/question-environment.sh").read_bytes(),
                                 SCRIPT.read_bytes())


if __name__ == "__main__":
    unittest.main()
