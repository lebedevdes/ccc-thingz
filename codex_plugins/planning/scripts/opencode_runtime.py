"""OpenCode 2 transport and permission narrowing; bundled in each standalone plugin."""

import json
import os
import re
import signal
import subprocess


def run_command(command, env, timeout):
    process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, text=True, env=env, start_new_session=True)
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except BaseException:
        # The child owns a separate process group, so cancelling the caller alone
        # cannot stop it. Reap it before propagating timeout or interruption.
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            process.communicate(timeout=2)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.communicate()
        raise
    return stdout, stderr, process.returncode


def readonly_environment(command, timeout):
    env = dict(os.environ)
    try:
        inline = json.loads(env.get("OPENCODE_CONFIG_CONTENT") or "{}")
        if not isinstance(inline, dict):
            raise ValueError("expected an object")
    except ValueError as exc:
        raise ValueError(f"Invalid OPENCODE_CONFIG_CONTENT: {exc}") from exc

    # Let OpenCode resolve defaults, global/project config, legacy config and
    # agent files. Reading just the inline JSON would miss inherited restrictions.
    stdout, stderr, code = run_command([*command, "debug", "agents"], env, timeout)
    if code:
        raise ValueError("Cannot resolve OpenCode permissions (requires OpenCode 2.2.5+): "
                         + (stderr.strip() or f"exit {code}"))
    try:
        agents = json.loads(stdout)
        if not isinstance(agents, list):
            raise ValueError("expected an agent array")
        plan = next(agent for agent in agents if agent.get("id") == "plan")
        original = plan["permissions"]
        if not isinstance(original, list):
            raise ValueError("expected permission rules")
        rules = [{"action": "*", "resource": "*", "effect": "deny"}]
        for rule in original:
            action, resource, effect = rule["action"], rule["resource"], rule["effect"]
            if not isinstance(action, str) or not isinstance(resource, str) or effect not in ("allow", "ask", "deny"):
                raise ValueError("invalid permission rule")
            # OpenCode uses only * and ? wildcards (not shell character classes).
            pattern = re.escape(action).replace(r"\*", ".*").replace(r"\?", ".")
            for tool in ("read", "glob", "grep", "list"):
                if re.fullmatch(pattern, tool):
                    rules.append({"action": tool, "resource": resource,
                                  "effect": "deny" if effect == "ask" else effect})
        # Native V2 rules are appended after inherited rules. Broad allows above
        # are expanded only to reading tools, so custom/MCP tools remain denied.
        inline.setdefault("agents", {}).setdefault("plan", {})["permissions"] = rules
    except (ValueError, KeyError, TypeError, AttributeError, StopIteration) as exc:
        raise ValueError(f"Cannot resolve OpenCode plan permissions: {exc}") from exc
    env["OPENCODE_CONFIG_CONTENT"] = json.dumps(inline)
    return env
