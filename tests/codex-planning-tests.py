"""Behavior checks for the Codex planning adaptation; no external model calls."""

import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import signal
import time
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "codex_plugins/planning/scripts"
sys.path.insert(0, str(SCRIPTS))
from planning_config import load_config


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


review = module("external_review", SCRIPTS / "run-external-review.py")
annotate = module("plan_annotate", SCRIPTS / "plan-annotate.py")


def text_event(text, message="final"):
    return json.dumps({"type": "text", "part": {"type": "text", "messageID": message, "text": text}})


class Fixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="codex planning ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = self.root / "project with spaces"
        self.project.mkdir()
        self.user = self.root / "user with spaces"
        self.user.mkdir()
        self.env = dict(os.environ, CODEX_HOME=str(self.user))
        for key in ("PLANNING_EXTERNAL_REVIEW_PROVIDER", "PLANNING_EXTERNAL_REVIEW_MODEL", "OPENCODE_CONFIG_CONTENT"):
            self.env.pop(key, None)

    def config(self, values, user=False):
        path = self.user / "planning.json" if user else self.project / ".codex/planning.json"
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(values))

    def run_script(self, script, *args, check=True):
        executable = "python3" if script.endswith(".py") else "bash"
        return subprocess.run([executable, str(SCRIPTS / script), *map(str, args)],
                              cwd=self.project, env=self.env, capture_output=True, text=True, check=check)

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.project, env=self.env,
                              capture_output=True, text=True, check=True).stdout


class ConfigTests(Fixture):
    def load(self):
        with patch.dict(os.environ, self.env, clear=True):
            return load_config(self.project)

    def test_default_provider_and_model(self):
        self.assertEqual(self.load()["external_review_provider"], "deepseek")
        self.assertEqual(self.load()["external_review_model"], "deepseek-flash")

    def test_subagent_model_defaults_to_unset(self):
        self.assertEqual(self.load()["subagent_model"], "")

    def test_subagent_model_precedence_and_normalization(self):
        self.config({"subagent_model": " user-model "}, user=True)
        self.assertEqual(self.load()["subagent_model"], "user-model")
        self.config({"subagent_model": " project-model "})
        config = self.load()
        self.assertEqual(config["subagent_model"], "project-model")
        self.assertEqual(config["external_review_model"], "deepseek-flash")

    def test_project_can_clear_user_subagent_model(self):
        self.config({"subagent_model": "user-model"}, user=True)
        for value in ("", " \t\n"):
            with self.subTest(value=value):
                self.config({"subagent_model": value})
                self.assertEqual(self.load()["subagent_model"], "")

    def test_subagent_model_rejects_non_strings(self):
        for value in (None, True, 1, [], {}):
            with self.subTest(value=value):
                self.config({"subagent_model": value})
                with self.assertRaisesRegex(ValueError, "subagent_model"):
                    self.load()

    def test_project_overrides_user_by_key(self):
        self.config({"external_review_provider": "gateway", "external_review_model": "vendor/model", "task_retries": 3}, user=True)
        self.config({"external_review_model": "other-model"})
        config = self.load()
        self.assertEqual((config["external_review_provider"], config["external_review_model"], config["task_retries"]), ("gateway", "other-model", 3))

    def test_environment_overrides_both_levels(self):
        self.config({"external_review_provider": "project", "external_review_model": "project-model"})
        self.env.update(PLANNING_EXTERNAL_REVIEW_PROVIDER="env-provider", PLANNING_EXTERNAL_REVIEW_MODEL="env-model")
        self.assertEqual(self.load()["external_review_provider"], "env-provider")
        self.assertEqual(self.load()["external_review_model"], "env-model")

    def test_invalid_values_are_not_silently_defaulted(self):
        for values in ({"task_retries": True}, {"review_iterations": 0}, {"external_review_timeout": -1},
                       {"finalize_enabled": "false"}, {"external_review_model": ""},
                       {"external_review_provider": "a/b"}, {"opencode_command": "opencode"}, {"typo": 1}):
            with self.subTest(values=values):
                self.config(values)
                with self.assertRaises(ValueError):
                    self.load()

    def test_malformed_json(self):
        self.config({})
        (self.project / ".codex/planning.json").write_text("{broken")
        with self.assertRaises(ValueError):
            self.load()


class OutputTests(unittest.TestCase):
    def test_ignore_tools_thinking_and_interim_commentary(self):
        events = [text_event("CRITICAL: just echoing the task", "interim"),
                  json.dumps({"type": "reasoning", "part": {"text": "MAJOR: internal thought"}}),
                  json.dumps({"type": "tool_use", "part": {"text": "CRITICAL: echoed source"}}),
                  text_event("NO ISSUES FOUND")]
        self.assertEqual(review.classify(review.review_text("\n".join(events)))["status"], "clean")

    def test_findings_win_over_incidental_clean_marker(self):
        result = review.classify("NO ISSUES FOUND\nMAJOR: src.py:4 - lost data\n  details")
        self.assertEqual(result["status"], "findings")
        self.assertTrue(result["has_blocking"])
        self.assertIn("details", result["text"])

    def test_minor_result(self):
        self.assertFalse(review.classify("- MINOR: README.md:1 - typo")["has_blocking"])

    def test_reject_empty_unstructured_or_malformed(self):
        for output in ("", "not JSON", "[]", json.dumps({"type": "error", "error": "bad model"})):
            with self.subTest(output=output), self.assertRaises(review.ReviewError):
                review.review_text(output)
        for output in ("", "I found no issues", "See CRITICAL in the source", "NO ISSUES FOUND but I could not read the files"):
            with self.subTest(output=output), self.assertRaises(review.ReviewError):
                review.classify(output)


FAKE = r'''
import json, os, pathlib, sys, time
args = sys.argv[1:]
if "debug" in args:
    if os.environ.get("FAKE_CASE") == "debug-timeout":
        pathlib.Path(os.environ["BACKEND_PID"]).write_text(str(os.getpid()))
        time.sleep(30)
    if os.environ.get("FAKE_CASE") == "bad-permissions":
        print("invalid")
        sys.exit(0)
    rules = json.loads(os.environ.get("EFFECTIVE_PERMISSIONS", '[{"action":"*","resource":"*","effect":"allow"},{"action":"read","resource":"*.env","effect":"ask"}]'))
    print(json.dumps([{"id":"plan", "permissions":rules}]))
    sys.exit(0)
pathlib.Path(os.environ["CAPTURE"]).write_text(json.dumps({
    "args": args,
    "inline": json.loads(os.environ["OPENCODE_CONFIG_CONTENT"]),
    "prompt": pathlib.Path(args[args.index("--file") + 1]).read_text(),
    "stdin": sys.stdin.read(),
}))
case = os.environ.get("FAKE_CASE", "clean")
if case == "exit127":
    print("inner tool missing", file=sys.stderr)
    sys.exit(127)
if case == "timeout":
    print(json.dumps({"type":"text", "part":{"text":"NO ISSUES FOUND"}}), flush=True)
    pathlib.Path(os.environ["BACKEND_PID"]).write_text(str(os.getpid()))
    time.sleep(30)
if case == "empty":
    sys.exit(0)
if case == "error":
    print(json.dumps({"type":"error", "error":"unknown model"}))
    sys.exit(0)
print("CRITICAL: prompt echo on stderr", file=sys.stderr)
text = "MAJOR: code.py:1 - real defect" if case == "findings" else "NO ISSUES FOUND"
print(json.dumps({"type":"text", "part":{"type":"text", "text":text}}))
'''


class RunnerTests(Fixture):
    def setUp(self):
        super().setUp()
        self.fake = self.root / "fake opencode.py"
        self.fake.write_text(FAKE)
        self.config({"opencode_command": [sys.executable, str(self.fake)], "external_review_timeout": 2})
        self.prompt = self.root / "prompt with spaces.md"
        self.prompt.write_text("Review `literal` and $(touch INJECTION) without expanding $variables.\n")
        self.capture = self.root / "capture.json"
        self.env["CAPTURE"] = str(self.capture)
        self.pid_file = self.root / "backend.pid"
        self.env["BACKEND_PID"] = str(self.pid_file)

    def run_review(self, *extra):
        result = self.run_script("run-external-review.py", self.prompt, *extra, check=False)
        return json.loads(result.stdout), result.returncode

    def test_permission_restrictions_survive_narrowing(self):
        rules = [
            {"action": "*", "resource": "*", "effect": "allow"},
            {"action": "read", "resource": "*.env", "effect": "ask"},
            {"action": "read", "resource": "private/*", "effect": "deny"},
            {"action": "g*", "resource": "secret*", "effect": "deny"},
            {"action": "read", "resource": "*.env.example", "effect": "allow"},
            {"action": "edit", "resource": "*", "effect": "allow"},
        ]
        self.env["EFFECTIVE_PERMISSIONS"] = json.dumps(rules)
        result, code = self.run_review()
        self.assertEqual(code, 0, result)
        narrowed = json.loads(self.capture.read_text())["inline"]["agents"]["plan"]["permissions"]
        import fnmatch
        def effect(action, resource):
            matches = [r["effect"] for r in narrowed if fnmatch.fnmatchcase(action, r["action"]) and fnmatch.fnmatchcase(resource, r["resource"])]
            return matches[-1] if matches else "ask"
        for action, resource, expected in (
            ("read", "code.py", "allow"), ("read", ".env", "deny"),
            ("read", "private/key", "deny"), ("read", ".env.example", "allow"),
            ("grep", "secret-value", "deny"), ("glob", "secret*", "deny"),
            ("shell", "git status", "deny"), ("edit", "file", "deny"),
            ("subagent", "general", "deny"), ("external_directory", "/tmp/*", "deny"),
            ("custom_mcp_write", "*", "deny"), ("question", "*", "deny")):
            with self.subTest(action=action, resource=resource):
                self.assertEqual(effect(action, resource), expected)

    def test_permission_discovery_failure_does_not_run_review(self):
        self.env["FAKE_CASE"] = "bad-permissions"
        result, code = self.run_review()
        self.assertEqual((result["status"], code), ("failed", 1))
        self.assertFalse(self.capture.exists())

    def test_default_selector_attachment_and_no_shell_expansion(self):
        result, code = self.run_review()
        self.assertEqual((result["status"], code), ("clean", 0))
        captured = json.loads(self.capture.read_text())
        self.assertEqual(captured["args"][captured["args"].index("--model") + 1], "deepseek/deepseek-flash")
        self.assertEqual(captured["prompt"], self.prompt.read_text())
        self.assertEqual(captured["stdin"], "")
        self.assertFalse((self.project / "INJECTION").exists())
        self.assertEqual(captured["inline"]["agents"]["plan"]["permissions"][0], {"action": "*", "resource": "*", "effect": "deny"})

    def test_custom_provider_model_and_existing_inline_config(self):
        self.env.update(PLANNING_EXTERNAL_REVIEW_PROVIDER="gateway", PLANNING_EXTERNAL_REVIEW_MODEL="vendor/model",
                        OPENCODE_CONFIG_CONTENT=json.dumps({"provider": {"gateway": {"name": "Existing"}}}))
        result, code = self.run_review()
        self.assertEqual(result["model"], "gateway/vendor/model")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(self.capture.read_text())["inline"]["provider"]["gateway"]["name"], "Existing")

    def test_subagent_model_does_not_override_external_reviewer(self):
        config = json.loads((self.project / ".codex/planning.json").read_text())
        config["subagent_model"] = "native-review-model"
        self.config(config)
        result, code = self.run_review()
        self.assertEqual((result["status"], result["model"], code),
                         ("clean", "deepseek/deepseek-flash", 0))
        args = json.loads(self.capture.read_text())["args"]
        self.assertEqual(args[args.index("--model") + 1], "deepseek/deepseek-flash")

    def test_findings(self):
        self.env["FAKE_CASE"] = "findings"
        result, code = self.run_review()
        self.assertEqual((result["status"], result["has_blocking"], code), ("findings", True, 0))

    def test_missing_executable_is_skipped(self):
        self.config({"opencode_command": [str(self.root / "missing-executable")]})
        result, code = self.run_review()
        self.assertEqual((result["status"], code), ("skipped", 127))

    def test_wrapper_failure_empty_and_error_are_failed(self):
        for case in ("exit127", "empty", "error"):
            with self.subTest(case=case):
                self.env["FAKE_CASE"] = case
                result, code = self.run_review()
                self.assertEqual(result["status"], "failed")
                self.assertNotEqual(code, 0)

    def test_timeout_discards_partial_clean_answer(self):
        self.env["FAKE_CASE"] = "timeout"
        self.config({"opencode_command": [sys.executable, str(self.fake)], "external_review_timeout": 1})
        result, code = self.run_review()
        self.assertEqual((result["status"], code), ("failed", 124))
        self.assertNotIn("text", result)

    def test_invalid_inline_config_does_not_launch(self):
        self.env["OPENCODE_CONFIG_CONTENT"] = "invalid"
        result, code = self.run_review()
        self.assertEqual((result["status"], code), ("failed", 1))
        self.assertFalse(self.capture.exists())

    def test_plan_and_progress_outside_project_are_attached(self):
        plan = self.root / "external plan.md"
        progress = self.root / "external progress.txt"
        plan.write_text("# Actual plan\n")
        progress.write_text("Prior review found a missing check.\n")
        result, code = self.run_review("--plan-file", plan, "--progress-file", progress)
        self.assertEqual((result["status"], code), ("clean", 0))
        prompt = json.loads(self.capture.read_text())["prompt"]
        self.assertIn(plan.read_text(), prompt)
        self.assertIn(progress.read_text(), prompt)

    def test_sigterm_stops_the_external_process(self):
        self.check_sigterm("timeout")

    def test_sigterm_stops_permission_discovery(self):
        self.check_sigterm("debug-timeout")

    def check_sigterm(self, case):
        self.env["FAKE_CASE"] = case
        process = subprocess.Popen([sys.executable, str(SCRIPTS / "run-external-review.py"), str(self.prompt)],
                                   cwd=self.project, env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            deadline = time.monotonic() + 5
            while not self.pid_file.exists() and process.poll() is None and time.monotonic() < deadline:
                time.sleep(0.02)
            self.assertTrue(self.pid_file.exists(), "Fake backend did not start")
            backend_pid = int(self.pid_file.read_text())
            process.send_signal(signal.SIGTERM)
            stdout, stderr = process.communicate(timeout=5)
            self.assertEqual(json.loads(stdout)["status"], "failed", stderr)
            with self.assertRaises(ProcessLookupError):
                os.kill(backend_pid, 0)
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate()
            if self.pid_file.exists():
                try:
                    os.killpg(int(self.pid_file.read_text()), signal.SIGKILL)
                except ProcessLookupError:
                    pass

    def test_snapshot_includes_committed_and_uncommitted_fixes(self):
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.name", "Test")
        self.git("config", "user.email", "test@example.invalid")
        source = self.project / "source.txt"
        source.write_text("initial\n")
        self.git("add", "source.txt")
        self.git("commit", "-qm", "Initial")
        self.git("switch", "-qc", "feature")
        source.write_text("committed fix\n")
        self.git("commit", "-qam", "Fix")
        source.write_text("committed fix\nworking fix\n")
        (self.project / "new.txt").write_text("untracked\n")
        result, code = self.run_review("--diff-base", "main")
        self.assertEqual((result["status"], code), ("clean", 0))
        prompt = json.loads(self.capture.read_text())["prompt"]
        for expected in ("-initial", "+committed fix", "+working fix", "new.txt"):
            self.assertIn(expected, prompt)
        source.write_text("index-only defect\n")
        self.git("add", source.name)
        source.write_text(self.git("show", "main:" + source.name))
        before = self.git("status", "--porcelain")
        result, code = self.run_review("--diff-base", "main")
        self.assertEqual(code, 0, result)
        prompt = json.loads(self.capture.read_text())["prompt"]
        self.assertIn("## Staged diff (HEAD to index)", prompt)
        self.assertIn("+index-only defect", prompt)
        self.assertIn("## Unstaged diff (index to working tree)", prompt)
        self.assertIn("-index-only defect", prompt)
        self.assertIn("## Git status", prompt)
        self.assertEqual(self.git("status", "--porcelain"), before)



class HelperTests(Fixture):
    def test_rules_project_precedence_and_empty_fallback(self):
        (self.project / ".codex").mkdir()
        project_rule = self.project / ".codex/planning-rules.md"
        project_rule.write_text("project")
        (self.user / "planning-rules.md").write_text("user")
        self.assertEqual(self.run_script("resolve-rules.sh", "planning-rules.md").stdout, "project")
        project_rule.write_text("")
        self.assertEqual(self.run_script("resolve-rules.sh", "planning-rules.md").stdout, "user")

    def test_prompt_overrides_and_empty_override(self):
        path = "prompts/task.md"
        default = self.run_script("resolve-file.sh", path).stdout
        self.assertEqual(default, (SCRIPTS.parent / "references" / path).read_text())
        user = self.user / "exec-plan" / path
        user.parent.mkdir(parents=True)
        user.write_text("user")
        self.assertEqual(self.run_script("resolve-file.sh", path).stdout, "user")
        project = self.project / ".codex/exec-plan" / path
        project.parent.mkdir(parents=True)
        project.write_text("")
        self.assertEqual(self.run_script("resolve-file.sh", path).stdout, "")

    def test_customization_copies_and_refuses_overwrite_and_traversal(self):
        self.run_script("customize-file.sh", "prompts/task.md")
        self.assertTrue((self.project / ".codex/exec-plan/prompts/task.md").is_file())
        self.assertNotEqual(self.run_script("customize-file.sh", "prompts/task.md", check=False).returncode, 0)
        self.assertNotEqual(self.run_script("customize-file.sh", "../outside", check=False).returncode, 0)

    def test_customization_refuses_symlinked_project_config(self):
        target = self.root / "outside"
        target.mkdir()
        (self.project / ".codex").symlink_to(target, target_is_directory=True)
        self.assertNotEqual(self.run_script("customize-file.sh", "prompts/task.md", check=False).returncode, 0)
        self.assertFalse((target / "exec-plan/prompts/task.md").exists())

    def test_annotation_outputs_feedback_without_changing_plan(self):
        plan = self.project / "plan.md"
        plan.write_text("# Original\n")
        def edit_copy(path, **kwargs):
            path.write_text("# Original\nPlease add error handling.\n")
            return 0
        with patch.dict(os.environ, {"PLANNING_DISABLE_REVDIFF": ""}), patch.object(annotate, "open_editor", edit_copy):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                annotate.run_file_mode(plan)
        self.assertIn("+Please add error handling.", output.getvalue())
        self.assertEqual(plan.read_text(), "# Original\n")

    def test_disabled_annotation_does_not_open_editor(self):
        with patch.dict(os.environ, {"PLANNING_DISABLE_REVDIFF": "1"}), patch.object(annotate, "open_editor") as editor:
            annotate.run_file_mode(self.project / "missing.md")
            editor.assert_not_called()

    def test_failed_agterm_overlay_is_not_accepted(self):
        from types import SimpleNamespace
        def run(command, **kwargs):
            return SimpleNamespace(returncode=7 if "overlay" in command else 0)
        with patch.dict(os.environ, {"AGTERM_SESSION_ID": "fixture"}, clear=True), patch.object(annotate.shutil, "which", return_value="/fake/tool"), patch.object(annotate.subprocess, "run", run):
            self.assertEqual(annotate.open_editor(self.project / "plan.md"), 7)

    def test_failed_kitty_launcher_returns_without_waiting(self):
        from types import SimpleNamespace
        with patch.dict(os.environ, {"KITTY_LISTEN_ON": "fixture"}, clear=True), patch.object(annotate.shutil, "which", return_value="/fake/tool"), patch.object(annotate.subprocess, "run", return_value=SimpleNamespace(returncode=9)):
            self.assertEqual(annotate.open_editor(self.project / "plan.md"), 9)

    def test_move_plan_preserves_unrelated_staged_changes(self):
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.name", "Test")
        self.git("config", "user.email", "test@example.invalid")
        plan = self.project / "docs/plans/custom.md"
        plan.parent.mkdir(parents=True)
        plan.write_text("# Done\n")
        other = self.project / "other.txt"
        other.write_text("before\n")
        self.git("add", ".")
        self.git("commit", "-qm", "Initial")
        other.write_text("unrelated user change\n")
        self.git("add", "other.txt")
        self.run_script("move-plan.sh", "docs/plans/custom.md")
        self.assertFalse(plan.exists())
        self.assertTrue((plan.parent / "completed/custom.md").exists())
        self.assertEqual(self.git("diff", "--cached", "--name-only").strip(), "other.txt")
        self.assertNotIn("other.txt", self.git("show", "--format=", "--name-only", "HEAD"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
