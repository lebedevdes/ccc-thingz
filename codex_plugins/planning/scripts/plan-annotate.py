#!/usr/bin/env python3
"""Annotate a copy of a plan in $EDITOR and print the unified diff.

Usage: plan-annotate.py <plan-file>
Supports agterm, tmux, kitty and wezterm overlays. No Codex lifecycle hook is installed.
"""

import difflib
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def review_disabled() -> bool:
    """report whether interactive plan review is disabled via PLANNING_DISABLE_REVDIFF.
    set this on a remote Codex client, where the editor overlay would
    open on the host terminal the remote client can't see and block the session."""
    return bool(os.environ.get("PLANNING_DISABLE_REVDIFF"))


def get_diff(original: str, edited: str) -> str:
    """get unified diff between original and edited content."""
    orig_lines = original.splitlines(keepends=True)
    edit_lines = edited.splitlines(keepends=True)
    diff = difflib.unified_diff(orig_lines, edit_lines, fromfile="original", tofile="annotated", n=2)
    return "".join(diff)


def build_editor_cmd(editor: str) -> str:
    """build a shell command string from a (possibly multi-word) $EDITOR value.

    splits $EDITOR into argv (e.g. "emacsclient -c -a ''" -> emacsclient, -c, -a, ''),
    resolves the first token to an absolute path (an overlay's sh doesn't inherit
    /opt/homebrew/bin etc.), and re-quotes each part. quoting the whole string as one
    token would exec a bogus binary name. falls back to vi on an empty or malformed
    (unbalanced-quote) $EDITOR instead of raising."""
    try:
        parts = shlex.split(editor) or ["vi"]  # guard set-but-empty $EDITOR
    except ValueError:
        parts = ["vi"]  # malformed $EDITOR, e.g. an unbalanced quote
    resolved = shutil.which(parts[0])
    if resolved:
        parts[0] = resolved
    return " ".join(shlex.quote(p) for p in parts)


def open_editor(filepath: Path, target_window: bool = False) -> int:
    """open file in $EDITOR via a terminal overlay, blocking until the editor closes.
    tries agterm first (if $AGTERM_SESSION_ID is set), then tmux (if $TMUX), then kitty,
    then wezterm. returns non-zero if none is available.
    when target_window is True, targets the kitty window from KITTY_WINDOW_ID.
    when False, opens in the currently focused window. agterm always targets the
    current session via $AGTERM_SESSION_ID, so target_window does not affect it."""
    editor_cmd = build_editor_cmd(os.environ.get("EDITOR", "vi"))

    # agterm: `agtermctl session overlay open <cmd> --block` opens the editor in a full-pane
    # overlay over the agent's own session and blocks until it exits (like tmux's display-popup -E),
    # so no sentinel is needed. checked first so an agterm session uses its native overlay even when
    # a multiplexer OR a stray KITTY_LISTEN_ON is also present in the environment. needs
    # $AGTERM_SESSION_ID (set in every agterm session) and agtermctl on PATH; passes $AGTERM_SOCKET
    # so it reaches the agterm instance hosting this session. the command string is shell-interpreted
    # by agterm, so the shell-quoted `editor_cmd` + filepath works. sets the session status indicator
    # to blocked while the overlay is up and restores active on every exit path.
    agterm_session = os.environ.get("AGTERM_SESSION_ID")
    if agterm_session and shutil.which("agtermctl"):
        target = ["--target", agterm_session]
        agterm_socket = os.environ.get("AGTERM_SOCKET")
        if agterm_socket:
            target += ["--socket", agterm_socket]
        # scope status and overlay to the active pane so the sibling stays live in a split session.
        # session status accepts left|right|scratch; overlay open only accepts left|right
        agterm_pane = os.environ.get("AGTERM_PANE")
        status_pane_args = ["--pane", agterm_pane] if agterm_pane else []
        overlay_pane_args = ["--pane", agterm_pane] if agterm_pane in ("left", "right") else []
        overlay_cmd = f"{editor_cmd} {shlex.quote(str(filepath))}"
        subprocess.run(
            ["agtermctl", "session", "status", "blocked", "--blink", *target, *status_pane_args],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        try:
            result = subprocess.run(
                ["agtermctl", "session", "overlay", "open", overlay_cmd, *target, *overlay_pane_args, "--block"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        finally:
            subprocess.run(
                ["agtermctl", "session", "status", "active", *target],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        return result.returncode

    # tmux: display-popup -E blocks until the command exits, no sentinel needed
    if os.environ.get("TMUX") and shutil.which("tmux"):
        result = subprocess.run(
            ["tmux", "display-popup", "-E", "-w", "90%", "-h", "90%",
             "-T", "Plan Review", "--", "sh", "-c",
             f'{editor_cmd} {shlex.quote(str(filepath))}'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        return result.returncode

    # kitty: use sentinel file to detect when editor closes.
    # requires KITTY_LISTEN_ON for socket communication — agent shell tools run
    # without a TTY, so kitty @ can't auto-detect via /dev/tty.
    # kitty.conf needs: allow_remote_control yes + listen_on unix:/tmp/kitty-$KITTY_PID
    kitty_sock = os.environ.get("KITTY_LISTEN_ON")
    if kitty_sock and shutil.which("kitty"):
        fd, sentinel_path = tempfile.mkstemp(prefix="plan-done-")
        os.close(fd)
        os.unlink(sentinel_path)
        sentinel = Path(sentinel_path)
        wrapper = f'{editor_cmd} {shlex.quote(str(filepath))}; touch {shlex.quote(str(sentinel))}'
        cmd = ["kitty", "@", "--to", kitty_sock, "launch", "--type=overlay",
               f"--title=Plan Review: {filepath.name}"]
        # optionally target the caller's window; otherwise use the focused window
        if target_window:
            kitty_wid = os.environ.get("KITTY_WINDOW_ID")
            if kitty_wid:
                cmd.extend(["--match", f"window_id:{kitty_wid}"])
        cmd.extend(["sh", "-c", wrapper])
        result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if result.returncode:
            sentinel.unlink(missing_ok=True)
            return result.returncode
        while not sentinel.exists():
            time.sleep(0.3)
        sentinel.unlink(missing_ok=True)
        return 0

    # wezterm: split-pane with sentinel file (same pattern as kitty)
    wezterm_pane = os.environ.get("WEZTERM_PANE")
    if wezterm_pane and shutil.which("wezterm"):
        fd, sentinel_path = tempfile.mkstemp(prefix="plan-done-")
        os.close(fd)
        os.unlink(sentinel_path)
        sentinel = Path(sentinel_path)
        wrapper = f'{editor_cmd} {shlex.quote(str(filepath))}; touch {shlex.quote(str(sentinel))}'
        result = subprocess.run(
            ["wezterm", "cli", "split-pane", "--bottom", "--percent", "80",
             "--pane-id", wezterm_pane, "--", "sh", "-c", wrapper],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        if result.returncode:
            sentinel.unlink(missing_ok=True)
            return result.returncode
        while not sentinel.exists():
            time.sleep(0.3)
        sentinel.unlink(missing_ok=True)
        return 0

    return 1


def run_file_mode(plan_file: Path) -> None:
    """file mode: open plan copy in editor, output diff to stdout."""
    if review_disabled():
        return
    if not plan_file.exists():
        print(f"error: file not found: {plan_file}", file=sys.stderr)
        sys.exit(1)

    plan_content = plan_file.read_text()

    # copy to temp file for annotation
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", prefix="plan-review-", delete=False) as tmp:
        tmp.write(plan_content)
        tmp_path = Path(tmp.name)

    try:
        if open_editor(tmp_path, target_window=False) != 0:
            print("error: no overlay terminal available (requires agterm, tmux, kitty, or wezterm)", file=sys.stderr)
            sys.exit(1)

        edited_content = tmp_path.read_text()
        diff = get_diff(plan_content, edited_content)

        if diff:
            print(diff)
    finally:
        tmp_path.unlink(missing_ok=True)


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Annotate a plan in an editor overlay")
    parser.add_argument("plan_file", type=Path)
    args = parser.parse_args()
    run_file_mode(args.plan_file)


if __name__ == "__main__":
    main()
