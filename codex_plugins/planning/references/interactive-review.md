# Interactive Plan Review

This is an explicit planning step; no lifecycle hooks are registered.

If `PLANNING_DISABLE_REVDIFF` is non-empty, report that interactive review is disabled and return to the next-step choice. Do not call the annotation tools or interpret the disabled path as user approval.

1. If `revdiff` is on PATH, run `bash <plugin-root>/scripts/launch-plan-review.sh <absolute-plan-path>` in the project root using an interactive-capable shell tool. The launcher supports agterm, tmux, zellij, herdr, orca, kitty, wezterm/kaku, cmux, Ghostty, iTerm2, and Emacs vterm overlays. Its stdout contains line-level annotations.
2. Otherwise run `python3 <plugin-root>/scripts/plan-annotate.py <absolute-plan-path>`. It opens a copy in `$EDITOR` using agterm, tmux, kitty, or wezterm and prints a unified diff. The original plan remains unchanged until Codex applies the feedback.
3. Show failures (missing editor, unavailable overlay, permissions, or nonzero exit) and offer conversation-based feedback. Never treat them as a completed review.
4. For successful non-empty output, address every annotation, show the resulting changes, and re-open the reviewer. Preserve the user's chosen scope when interpreting suggestions.
5. A successful run with no annotations ends the loop. Return to the remaining next-step options unless a subsequent action is already authorized.

While waiting for an interactive review or an external process, use the client's yielding/background mechanism when available and keep the user informed. Do not assume Claude Code's background notification APIs exist.
