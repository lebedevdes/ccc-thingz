#!/usr/bin/env python3
"""Behavioral checks for the Claude-derived OpenCode planning bundle."""

import base64
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request


ROOT = Path(__file__).resolve().parent.parent
PLUGIN = ROOT / "opencode_plugins/planning"
SCRIPTS = PLUGIN / "scripts"
EXEC = PLUGIN / "skills/planning-exec/scripts"


class PlanningTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="opencode-planning-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.project = self.base / "project with spaces"
        self.project.mkdir()
        self.user = self.base / "user config"
        self.env = dict(os.environ, OPENCODE_CONFIG_DIR=str(self.user),
                        GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
                        GIT_AUTHOR_NAME="Planning Test", GIT_AUTHOR_EMAIL="test@example.invalid",
                        GIT_COMMITTER_NAME="Planning Test", GIT_COMMITTER_EMAIL="test@example.invalid")

    def run_cmd(self, args, *, ok=True, env=None, cwd=None, input=None):
        result = subprocess.run([str(arg) for arg in args], cwd=cwd or self.project,
                                env=env or self.env, input=input, text=True,
                                capture_output=True, timeout=30)
        if ok:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def write(self, path, text):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def config(self, *, ok=True):
        return self.run_cmd([sys.executable, SCRIPTS / "planning_config.py"], ok=ok)

    def fake(self, name, body):
        script = self.write(self.base / "bin" / name, "#!/bin/bash\n" + body)
        script.chmod(0o755)
        self.env["PATH"] = str(script.parent) + os.pathsep + self.env["PATH"]
        return script

    def init_git(self):
        self.run_cmd(["git", "init", "-q", "-b", "main"])
        self.write(self.project / "README.md", "initial\n")
        self.run_cmd(["git", "add", "README.md"])
        self.run_cmd(["git", "commit", "-qm", "initial"])

    def test_config_defaults_and_fieldwise_precedence(self):
        defaults = json.loads(self.config().stdout)
        self.assertEqual(defaults["external_review_cmd"], "")
        self.assertEqual(defaults["review_iterations"], 5)
        self.assertEqual(defaults["plugin_root"], str(PLUGIN))
        self.assertEqual(defaults["plugin_data_dir"], str(self.user / "planning"))
        self.assertNotIn("plans_dir", defaults)
        self.write(self.user / "planning.json", json.dumps({"review_iterations": 2, "finalize_enabled": False}))
        self.write(self.project / ".opencode/planning.json", json.dumps({"task_retries": 0}))
        config = json.loads(self.config().stdout)
        self.assertEqual(config["review_iterations"], 2)
        self.assertFalse(config["finalize_enabled"])
        self.assertEqual(config["task_retries"], 0)

    def test_config_rejects_malformed_unknown_and_invalid_settings(self):
        for value in ("{", "[]", '{"typo": 1}', '{"task_retries": true}',
                      '{"review_iterations": 0}', '{"finalize_enabled": "false"}',
                      '{"subagent_model": "opus"}', '{"plans_dir": "docs/plans"}',
                      '{"external_review_cmd": "tool\\nother"}'):
            with self.subTest(value=value):
                self.write(self.project / ".opencode/planning.json", value)
                result = self.config(ok=False)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("planning config:", result.stderr)

    def test_xdg_config_resolution_and_shell_resolvers_agree(self):
        env = dict(self.env)
        env.pop("OPENCODE_CONFIG_DIR")
        env["XDG_CONFIG_HOME"] = str(self.base / "xdg config")
        user_data = Path(env["XDG_CONFIG_HOME"]) / "opencode/planning"
        self.write(user_data / "planning-rules.md", "user rules")
        config = json.loads(self.run_cmd([sys.executable, SCRIPTS / "planning_config.py"], env=env).stdout)
        self.assertEqual(config["plugin_data_dir"], str(user_data))
        rules = self.run_cmd(["bash", SCRIPTS / "resolve-rules.sh", "planning-rules.md"], env=env)
        self.assertEqual(rules.stdout, "user rules")

    def test_rules_first_nonempty_file_and_claude_separation(self):
        resolver = ["bash", SCRIPTS / "resolve-rules.sh", "planning-rules.md"]
        self.write(self.project / ".claude/planning-rules.md", "Claude only")
        self.assertEqual(self.run_cmd(resolver).stdout, "")
        self.write(self.user / "planning/planning-rules.md", "user")
        project_rules = self.write(self.project / ".opencode/planning-rules.md", "")
        self.assertEqual(self.run_cmd(resolver).stdout, "user")
        project_rules.write_text("project")
        self.assertEqual(self.run_cmd(resolver).stdout, "project")

    def test_prompt_override_precedence_and_opt_in_copy(self):
        resolver = ["bash", EXEC / "resolve-file.sh", "prompts/task.md"]
        bundled = (PLUGIN / "skills/planning-exec/references/prompts/task.md").read_text()
        self.assertEqual(self.run_cmd(resolver).stdout, bundled)
        self.assertFalse((self.user / "planning").exists())
        self.write(self.user / "planning/prompts/task.md", "user prompt")
        self.assertEqual(self.run_cmd(resolver).stdout, "user prompt")
        copy = self.run_cmd(["bash", EXEC / "customize-file.sh", "prompts/task.md"])
        destination = self.project / copy.stdout.strip()
        self.assertEqual(destination.read_text(), bundled)
        destination.write_text("project prompt")
        self.assertEqual(self.run_cmd(resolver).stdout, "project prompt")
        retry = self.run_cmd(["bash", EXEC / "customize-file.sh", "prompts/task.md"], ok=False)
        self.assertNotEqual(retry.returncode, 0)
        self.assertEqual(destination.read_text(), "project prompt")

    def test_override_copy_rejects_traversal_and_project_symlink(self):
        result = self.run_cmd(["bash", EXEC / "customize-file.sh", "../outside.md"], ok=False)
        self.assertIn("path must be relative", result.stderr)
        outside = self.base / "outside"
        outside.mkdir()
        (self.project / ".opencode").symlink_to(outside, target_is_directory=True)
        result = self.run_cmd(["bash", EXEC / "customize-file.sh", "prompts/task.md"], ok=False)
        self.assertIn("symlinked directory", result.stderr)
        self.assertEqual(list(outside.iterdir()), [])

    def test_install_is_complete_and_does_not_change_preferences(self):
        prefs = self.write(self.user / "opencode.json", '{"default_agent":"build"}')
        settings = self.write(self.user / "planning.json", '{"finalize_enabled":false}')
        cmd = [sys.executable, SCRIPTS / "install.py"]
        self.run_cmd([*cmd, "--dry-run"])
        self.assertEqual(sorted(p.name for p in self.user.iterdir()), ["opencode.json", "planning.json"])
        self.run_cmd(cmd)
        bundle = self.user / "skills/planning"
        self.assertTrue((bundle / ".ccc-thingz-planning").is_file())
        self.assertFalse(bundle.is_symlink())
        self.assertTrue((bundle / "skills/planning-exec/SKILL.md").is_file())
        self.assertFalse((bundle / "skills/planning-make").exists())
        for name in ("make", "exec"):
            command = (self.user / "commands" / f"planning:{name}.md").read_text()
            self.assertIn("$ARGUMENTS", command)
            self.assertIn("subagent: false", command)
        make_command = (self.user / "commands/planning:make.md").read_text()
        self.assertIn("Implementation Plan Creation", make_command)
        self.assertIn(str(bundle), make_command)
        self.assertIn("planning-exec", (self.user / "commands/planning:exec.md").read_text())
        self.assertTrue((bundle / "skills/planning-exec/scripts/resolve-file.sh").is_file())
        self.assertTrue((bundle / "scripts/planning_config.py").is_file())
        for name in ("plan-review", "external-plan-review"):
            agent = (self.user / "agents" / f"planning-{name}.md").read_text()
            self.assertIn(str(bundle), agent)
            self.assertIn("mode: subagent", agent)
        stale = bundle / "stale.txt"
        stale.write_text("old")
        self.run_cmd(cmd)
        self.assertFalse(stale.exists())
        self.assertEqual(prefs.read_text(), '{"default_agent":"build"}')
        self.assertEqual(settings.read_text(), '{"finalize_enabled":false}')

    def test_install_preflights_conflicts_without_partial_install(self):
        target = self.project / ".opencode"
        conflict = self.write(target / "agents/planning-plan-review.md", "my agent")
        result = self.run_cmd([sys.executable, SCRIPTS / "install.py", "--project", self.project], ok=False)
        self.assertIn("Refusing to overwrite", result.stderr)
        self.assertEqual(conflict.read_text(), "my agent")
        self.assertFalse((target / "skills").exists())

    def test_reinstall_overwrites_managed_files_and_refuses_unrelated(self):
        cmd = [sys.executable, SCRIPTS / "install.py", "--target", self.user]
        self.run_cmd(cmd)
        wrapper = self.user / "commands/planning:make.md"
        original = wrapper.read_text()
        wrapper.write_text(original + "\nold generated content\n")
        self.run_cmd(cmd)
        self.assertEqual(wrapper.read_text(), original)
        wrapper.write_text("unrelated command")
        self.assertNotEqual(self.run_cmd(cmd, ok=False).returncode, 0)
        self.assertEqual(wrapper.read_text(), "unrelated command")

    def test_install_refuses_unmanaged_bundle(self):
        bundle = self.user / "skills/planning"
        bundle.mkdir(parents=True)
        marker = self.write(bundle / "mine.txt", "keep me")
        result = self.run_cmd([sys.executable, SCRIPTS / "install.py", "--target", self.user], ok=False)
        self.assertIn("not this installer's planning bundle", result.stderr)
        self.assertEqual(marker.read_text(), "keep me")
        self.assertFalse((self.user / "commands").exists())

    def test_installed_copy_refuses_to_overwrite_itself(self):
        cmd = [sys.executable, SCRIPTS / "install.py", "--target", self.user]
        self.run_cmd(cmd)
        copied = self.user / "skills/planning/scripts/install.py"
        result = self.run_cmd([sys.executable, copied, "--target", self.user], ok=False)
        self.assertIn("source checkout", result.stderr)
        self.assertTrue((self.user / "skills/planning/skills/planning-exec/SKILL.md").is_file())

    def test_external_review_argv_stdin_and_stderr_contract(self):
        self.fake("fake-reviewer", 'printf "CRITICAL echoed prompt on stderr\\n" >&2\n'
                  'python3 -c \'import json,sys; print(json.dumps({"args":sys.argv[1:],"stdin":sys.stdin.read()}))\' "$@"\n')
        self.write(self.project / ".opencode/planning.json", '{"external_review_cmd":"fake-reviewer review --strict"}')
        prompt = "Review `code` and $(touch SHOULD_NOT_EXIST); $HOME; 'quotes'\nUnicode: привет"
        prompt_file = self.write(self.project / "prompt with spaces.txt", prompt)
        result = self.run_cmd([sys.executable, SCRIPTS / "run-review.py", prompt_file], input="inherited pipe")
        output = json.loads(result.stdout)
        self.assertEqual(output["args"], ["review", "--strict", prompt])
        self.assertEqual(output["stdin"], "")
        self.assertIn("CRITICAL", result.stderr)
        self.assertFalse((self.project / "SHOULD_NOT_EXIST").exists())

    def test_external_review_config_failure_does_not_run_default(self):
        self.fake("codex", 'touch CODEX_WAS_RUN\n')
        self.write(self.project / ".opencode/planning.json", '{"typo": true}')
        prompt = self.write(self.project / "prompt.txt", "review")
        result = self.run_cmd([sys.executable, SCRIPTS / "run-review.py", prompt], ok=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Unknown settings", result.stderr)
        self.assertFalse((self.project / "CODEX_WAS_RUN").exists())

    def test_external_missing_tool_marker_and_reviewer_failure_are_distinct(self):
        prompt = self.write(self.project / "prompt.txt", "review")
        config = self.project / ".opencode/planning.json"
        self.write(config, '{"external_review_cmd":"ccc-nonexistent-reviewer-1234"}')
        result = self.run_cmd([sys.executable, SCRIPTS / "run-review.py", prompt], ok=False)
        self.assertEqual(result.returncode, 127)
        self.assertIn("run-external-review:", result.stderr)
        self.fake("fails", 'echo "inner tool missing" >&2\nexit 127\n')
        config.write_text('{"external_review_cmd":"fails"}')
        result = self.run_cmd([sys.executable, SCRIPTS / "run-review.py", prompt], ok=False)
        self.assertEqual(result.returncode, 127)
        self.assertNotIn("run-external-review:", result.stderr)

    def test_default_external_review_is_original_codex_readonly_launcher(self):
        self.init_git()
        self.fake("codex", 'python3 -c \'import json,sys; print(json.dumps(sys.argv[1:]))\' "$@"\n')
        prompt = self.write(self.project / "prompt.txt", "review all changes")
        args = json.loads(self.run_cmd([sys.executable, SCRIPTS / "run-review.py", prompt]).stdout)
        self.assertEqual(args[:3], ["exec", "--sandbox", "read-only"])
        self.assertEqual(args[-1], "review all changes")

    def test_git_plan_lifecycle_preserves_unrelated_staged_changes(self):
        self.init_git()
        plan = self.write(self.project / "docs/plans/20261104-feature.md", "### Task 1: Example\n- [ ] implement\n")
        self.run_cmd(["bash", EXEC / "stage-and-commit.sh", "docs: plan", plan])
        branch = self.run_cmd(["bash", EXEC / "create-branch.sh", plan]).stdout.strip()
        self.assertEqual(branch, "feature")
        unrelated = self.write(self.project / "unrelated.txt", "user work\n")
        self.run_cmd(["git", "add", unrelated])
        plan.write_text(plan.read_text().replace("[ ]", "[x]"))
        source = self.write(self.project / "feature.txt", "implemented\n")
        self.run_cmd(["bash", EXEC / "stage-and-commit.sh", "feat: example", source, plan])
        self.assertEqual(self.run_cmd(["git", "diff", "--cached", "--name-only"]).stdout.strip(), "unrelated.txt")
        progress = self.project / "progress.txt"
        self.run_cmd(["bash", EXEC / "init-progress.sh", progress, plan, branch])
        self.run_cmd(["bash", EXEC / "append-progress.sh", progress, "[decision] task 1: simple implementation"])
        self.assertIn("[decision] task 1", progress.read_text())
        result = self.run_cmd(["bash", EXEC / "move-plan.sh", plan])
        self.assertIn("moved plan to", result.stdout)
        self.assertFalse(plan.exists())
        completed = plan.parent / "completed" / plan.name
        self.assertTrue(completed.exists())
        self.assertEqual(self.run_cmd(["git", "diff", "--cached", "--name-only"]).stdout.strip(), "unrelated.txt")

    def test_worktree_branch_derivation_has_no_original_checkout_side_effects(self):
        self.init_git()
        before = self.run_cmd(["git", "rev-parse", "HEAD"]).stdout
        name = self.run_cmd(["bash", EXEC / "create-branch.sh", "--print-name", "docs/plans/20261104-isolation.md"]).stdout.strip()
        worktree = self.base / "isolated tree"
        self.run_cmd(["git", "worktree", "add", "-b", name, worktree, "HEAD"])
        self.assertEqual(self.run_cmd(["git", "branch", "--show-current"]).stdout.strip(), "main")
        self.assertEqual(self.run_cmd(["git", "rev-parse", "HEAD"]).stdout, before)
        self.assertEqual(self.run_cmd(["git", "status", "--porcelain"]).stdout, "")
        self.assertEqual(self.run_cmd(["git", "branch", "--show-current"], cwd=worktree).stdout.strip(), name)

    @unittest.skipUnless(os.environ.get("OPENCODE_PLANNING_LIVE"), "optional native OpenCode discovery check")
    def test_native_discovery(self):
        env = dict(self.env)
        for variable, directory in (("XDG_CONFIG_HOME", "config"), ("XDG_DATA_HOME", "data"),
                                    ("XDG_CACHE_HOME", "cache"), ("XDG_STATE_HOME", "state")):
            env[variable] = str(self.base / directory)
        for variable in ("OPENCODE_CONFIG", "OPENCODE_CONFIG_CONTENT", "OPENCODE_DB"):
            env.pop(variable, None)
        self.run_cmd([sys.executable, SCRIPTS / "install.py"], env=env)
        result = self.run_cmd(["opencode", "debug", "agents", "--standalone"], env=env)
        agents = {agent["id"]: agent for agent in json.loads(result.stdout)}
        for name in ("planning-plan-review", "planning-external-plan-review"):
            self.assertIn(name, agents)
            self.assertEqual(agents[name]["mode"], "subagent")

    @unittest.skipUnless(os.environ.get("OPENCODE_PLANNING_LIVE"), "optional native OpenCode registration check")
    def test_native_skill_and_command_registration(self):
        self.init_git()
        env = dict(self.env)
        for variable in ("XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_CACHE_HOME", "XDG_STATE_HOME"):
            env[variable] = str(self.base / variable)
        for variable in ("OPENCODE_CONFIG", "OPENCODE_CONFIG_CONTENT", "OPENCODE_DB"):
            env.pop(variable, None)
        self.run_cmd([sys.executable, SCRIPTS / "install.py", "--project", self.project], env=env)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        with tempfile.TemporaryFile(mode="w+") as logs:
            server = subprocess.Popen(["opencode", "serve", "--hostname", "127.0.0.1", "--port", str(port)],
                                      cwd=self.project, env=env, stdin=subprocess.DEVNULL,
                                      stdout=logs, stderr=logs)
            try:
                base = f"http://127.0.0.1:{port}"
                def request(path, timeout=10):
                    logs.seek(0)
                    match = re.search(r"server password (\S+)", logs.read())
                    headers = {}
                    if match:
                        token = base64.b64encode(f"opencode:{match[1]}".encode()).decode()
                        headers["Authorization"] = "Basic " + token
                    return urllib.request.urlopen(urllib.request.Request(base + path, headers=headers), timeout=timeout)

                deadline = time.monotonic() + 15
                while True:
                    try:
                        with request("/api/info", timeout=1) as response:
                            json.load(response)
                        break
                    except (urllib.error.URLError, TimeoutError):
                        if server.poll() is not None or time.monotonic() > deadline:
                            logs.seek(0)
                            output = re.sub(r"server password \S+", "server password <redacted>", logs.read())
                            self.fail("Isolated OpenCode server did not start: " + output)
                        time.sleep(0.05)
                query = urllib.parse.urlencode({"location[directory]": str(self.project)})
                for resource, key, required in (
                    ("skill", "id", {"planning-exec"}),
                    ("command", "name", {"planning:make", "planning:exec"}),
                ):
                    with self.subTest(resource=resource):
                        deadline = time.monotonic() + 5
                        while True:
                            with request(f"/api/{resource}?{query}") as response:
                                payload = json.load(response)
                                registered = payload["data"]
                            self.assertEqual(Path(payload["location"]["directory"]).resolve(), self.project)
                            if required.issubset({entry[key] for entry in registered}):
                                break
                            if time.monotonic() > deadline:
                                self.fail(f"Missing {resource}: {registered}")
                            time.sleep(0.05)
            finally:
                server.terminate()
                try:
                    server.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait(timeout=5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
