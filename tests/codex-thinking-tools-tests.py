"""Behavior checks for thinking-tools' bundled OpenCode consultation."""

import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "codex_plugins/thinking-tools/scripts"
sys.path.insert(0, str(SCRIPTS))
from opencode_config import load_config


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


ask = module("ask_opencode", SCRIPTS / "ask-opencode.py")
planning_config = module("planning_config_reference", ROOT / "codex_plugins/planning/scripts/planning_config.py")


def valid_review(findings=False):
    return {
        "verdict": "needs-attention" if findings else "approve",
        "summary": "A supported defect" if findings else "No supported material issues",
        "findings": [{
            "severity": "high", "title": "Dropped error", "body": "An error is ignored on the retry path",
            "file": "code.py", "line_start": 2, "line_end": 3, "confidence": 0.85,
            "recommendation": "Propagate the error and test the failure path",
        }] if findings else [],
        "next_steps": ["Add a regression check"] if findings else [],
    }


class ReviewContractTests(unittest.TestCase):
    def test_approval_and_findings(self):
        for has_findings in (False, True):
            value = valid_review(has_findings)
            self.assertEqual(ask.parse_review(json.dumps(value)), value)

    def test_whole_json_fence_is_accepted(self):
        value = valid_review()
        self.assertEqual(ask.parse_review("```json\n" + json.dumps(value) + "\n```"), value)

    def test_low_confidence_findings_remain_visible(self):
        value = valid_review(True)
        value["findings"][0]["confidence"] = 0.1
        self.assertEqual(ask.parse_review(json.dumps(value))["findings"][0]["confidence"], 0.1)

    def test_invalid_fields_are_rejected(self):
        for key, invalid in (("severity", "severe"), ("line_start", True), ("line_end", 1),
                             ("confidence", True), ("confidence", -0.1), ("confidence", 1.1),
                             ("confidence", float("nan")), ("file", ""), ("recommendation", None)):
            value = valid_review(True)
            value["findings"][0][key] = invalid
            with self.subTest(key=key, invalid=invalid), self.assertRaises(ValueError):
                ask.parse_review(json.dumps(value))

    def test_contradictory_verdict_is_rejected(self):
        for has_findings in (False, True):
            value = valid_review(has_findings)
            value["verdict"] = "approve" if has_findings else "needs-attention"
            with self.subTest(has_findings=has_findings), self.assertRaises(ValueError):
                ask.parse_review(json.dumps(value))

    def test_non_review_output_is_rejected(self):
        for text in ("", "Looks good", "{}", "[]", "null", '{"verdict":"approve"}'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                ask.parse_review(text)


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
    "args": args, "inline": json.loads(os.environ["OPENCODE_CONFIG_CONTENT"]),
    "prompt": pathlib.Path(args[args.index("--file") + 1]).read_text(), "stdin": sys.stdin.read(),
}))
case = os.environ.get("FAKE_CASE", "advice")
if case == "exit127":
    print("inner executable missing", file=sys.stderr)
    sys.exit(127)
if case == "empty":
    sys.exit(0)
if case == "error":
    print(json.dumps({"type":"error", "error":"model unavailable"}))
    sys.exit(0)
if case == "invalid-events":
    print("not an event")
    sys.exit(0)
print(json.dumps({"type":"text", "part":{"messageID":"interim", "text":"Interim commentary"}}))
print(json.dumps({"type":"tool_use", "part":{"text":"ignore this tool result"}}))
print("stderr is not the answer", file=sys.stderr)
text = os.environ.get("REVIEW_RESPONSE", "The failure is caused by an unchecked error at code.py:2.")
print(json.dumps({"type":"text", "part":{"messageID":"final", "text":text}}), flush=True)
if case == "timeout":
    pathlib.Path(os.environ["BACKEND_PID"]).write_text(str(os.getpid()))
    time.sleep(30)
'''


class ConsultationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="thinking tools ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = self.root / "project with spaces"
        self.project.mkdir()
        self.user = self.root / "codex home"
        self.user.mkdir()
        self.fake = self.root / "fake opencode.py"
        self.fake.write_text(FAKE)
        self.prompt = self.root / "question.md"
        self.prompt.write_text("Investigate `literal` and $(touch INJECTION). Preserve $variables.\n")
        self.capture = self.root / "capture.json"
        self.pid_file = self.root / "backend.pid"
        self.env = dict(os.environ, CODEX_HOME=str(self.user), CAPTURE=str(self.capture), BACKEND_PID=str(self.pid_file))
        for key in ("PLANNING_EXTERNAL_REVIEW_PROVIDER", "PLANNING_EXTERNAL_REVIEW_MODEL", "OPENCODE_CONFIG_CONTENT", "REVIEW_RESPONSE", "FAKE_CASE"):
            self.env.pop(key, None)
        self.config({"opencode_command": [sys.executable, str(self.fake)], "external_review_timeout": 2})

    def config(self, values, user=False):
        path = self.user / "planning.json" if user else self.project / ".codex/planning.json"
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(values))

    def run_ask(self, *args):
        result = subprocess.run([sys.executable, str(SCRIPTS / "ask-opencode.py"), str(self.prompt), *map(str, args)],
                                cwd=self.project, env=self.env, capture_output=True, text=True)
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
        result, code = self.run_ask()
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
        result, code = self.run_ask()
        self.assertEqual((result["status"], code), ("failed", 1))
        self.assertFalse(self.capture.exists())

    def test_advice_uses_only_final_text_and_default_model(self):
        result, code = self.run_ask()
        self.assertEqual((result["status"], result["model"], code), ("completed", "deepseek/deepseek-flash", 0))
        self.assertIn("code.py:2", result["text"])
        self.assertNotIn("Interim", result["text"])
        self.assertNotIn("stderr", result["text"])
        captured = json.loads(self.capture.read_text())
        self.assertEqual(captured["prompt"], self.prompt.read_text())
        self.assertEqual(captured["stdin"], "")
        self.assertFalse((self.project / "INJECTION").exists())

    def test_bundled_runtime_matches_planning(self):
        self.assertEqual((SCRIPTS / "opencode_runtime.py").read_bytes(),
                         (ROOT / "codex_plugins/planning/scripts/opencode_runtime.py").read_bytes())

    def test_configuration_matches_planning_by_key_and_environment(self):
        self.config({"external_review_provider": "gateway", "external_review_model": "vendor/model", "task_retries": 2,
                     "subagent_model": " local-model "}, user=True)
        with patch.dict(os.environ, self.env, clear=True):
            self.assertEqual(load_config(self.project), planning_config.load_config(self.project))
            self.assertEqual(load_config(self.project)["external_review_provider"], "gateway")
            self.assertEqual(load_config(self.project)["subagent_model"], "local-model")
        self.env.update(PLANNING_EXTERNAL_REVIEW_PROVIDER="env-gateway", PLANNING_EXTERNAL_REVIEW_MODEL="env-model")
        result, code = self.run_ask()
        self.assertEqual((result["model"], code), ("env-gateway/env-model", 0))

    def test_provider_configuration_is_preserved_and_writes_denied(self):
        self.env["OPENCODE_CONFIG_CONTENT"] = json.dumps({"provider": {"gateway": {"name": "Existing"}}})
        self.run_ask()
        inline = json.loads(self.capture.read_text())["inline"]
        self.assertEqual(inline["provider"]["gateway"]["name"], "Existing")
        permissions = inline["agents"]["plan"]["permissions"]
        self.assertEqual(permissions[0], {"action": "*", "resource": "*", "effect": "deny"})
        self.assertTrue(all(rule["action"] in ("*", "read", "glob", "grep", "list") for rule in permissions))

    def test_context_attachments_are_literal_snapshots(self):
        context = self.root / "external context.txt"
        context.write_text("Результат проверки: `literal` $x $(touch BAD)\n")
        result, code = self.run_ask("--attach", context)
        self.assertEqual((result["status"], code), ("completed", 0))
        self.assertIn(context.read_text(), json.loads(self.capture.read_text())["prompt"])
        self.assertFalse((self.project / "BAD").exists())

    def test_structured_review_and_contract(self):
        value = valid_review(True)
        self.env["REVIEW_RESPONSE"] = json.dumps(value)
        result, code = self.run_ask("--mode", "review")
        self.assertEqual((result["status"], result["review"], code), ("reviewed", value, 0))
        self.assertIn('"confidence"', json.loads(self.capture.read_text())["prompt"])

    def test_invalid_review_is_a_failure(self):
        self.env["REVIEW_RESPONSE"] = "Looks good, I guess."
        result, code = self.run_ask("--mode", "review")
        self.assertEqual((result["status"], code), ("failed", 1))

    def test_missing_tool_is_skipped(self):
        self.config({"opencode_command": [str(self.root / "missing") ]})
        result, code = self.run_ask()
        self.assertEqual((result["status"], code), ("skipped", 127))

    def test_wrapper_error_empty_and_invalid_events_are_failures(self):
        for case in ("exit127", "empty", "error", "invalid-events"):
            with self.subTest(case=case):
                self.env["FAKE_CASE"] = case
                result, code = self.run_ask()
                self.assertEqual(result["status"], "failed")
                self.assertNotEqual(code, 0)

    def test_invalid_config_or_missing_context_prevents_launch(self):
        self.config({"unknown_setting": True})
        result, code = self.run_ask()
        self.assertEqual((result["status"], code), ("failed", 1))
        self.assertFalse(self.capture.exists())
        self.config({"opencode_command": [sys.executable, str(self.fake)]})
        result, code = self.run_ask("--attach", self.root / "missing context")
        self.assertEqual((result["status"], code), ("failed", 1))
        self.assertFalse(self.capture.exists())

    def test_timeout_discards_partial_answer(self):
        self.config({"opencode_command": [sys.executable, str(self.fake)], "external_review_timeout": 1})
        self.env["FAKE_CASE"] = "timeout"
        result, code = self.run_ask()
        self.assertEqual((result["status"], code), ("failed", 124))
        self.assertNotIn("text", result)

    def test_sigterm_stops_the_external_process(self):
        self.check_sigterm("timeout")

    def test_sigterm_stops_permission_discovery(self):
        self.check_sigterm("debug-timeout")

    def check_sigterm(self, case):
        self.env["FAKE_CASE"] = case
        process = subprocess.Popen([sys.executable, str(SCRIPTS / "ask-opencode.py"), str(self.prompt)],
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

    def test_branch_snapshot_includes_committed_and_working_changes(self):
        def git(*args):
            return subprocess.run(["git", *args], cwd=self.project, env=self.env, check=True, capture_output=True, text=True).stdout
        git("init", "-q", "-b", "main")
        git("config", "user.name", "Test")
        git("config", "user.email", "test@example.invalid")
        source = self.project / "code.txt"
        source.write_text("before\n")
        git("add", "code.txt")
        git("commit", "-qm", "Initial")
        git("switch", "-qc", "feature")
        source.write_text("committed\n")
        git("commit", "-qam", "Fix")
        source.write_text("committed\nworking\n")
        result, code = self.run_ask("--diff-base", "main")
        self.assertEqual((result["status"], code), ("completed", 0))
        prompt = json.loads(self.capture.read_text())["prompt"]
        for expected in ("-before", "+committed", "+working"):
            self.assertIn(expected, prompt)
        source.write_text("index-only defect\n")
        git("add", source.name)
        source.write_text(git("show", "main:" + source.name))
        before = git("status", "--porcelain")
        result, code = self.run_ask("--diff-base", "main")
        self.assertEqual(code, 0, result)
        prompt = json.loads(self.capture.read_text())["prompt"]
        self.assertIn("## Staged diff (HEAD to index)", prompt)
        self.assertIn("+index-only defect", prompt)
        self.assertIn("## Unstaged diff (index to working tree)", prompt)
        self.assertIn("-index-only defect", prompt)
        self.assertIn("## Git status", prompt)
        self.assertEqual(git("status", "--porcelain"), before)



if __name__ == "__main__":
    unittest.main(verbosity=2)
