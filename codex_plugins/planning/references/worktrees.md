# Branches and Worktrees

Honor an existing choice of isolation. Otherwise ask once: execute in the current checkout or a separate worktree? On an existing feature branch, explain that isolation creates a separate child branch from the current commit; it does not detach that branch from the original checkout.

## Current Checkout

Record existing user changes. Use `scripts/create-branch.sh <plan-file>` to create a feature branch from the date-stripped plan name when on the default branch, or keep the current feature branch. Never force-switch over unrelated changes or include them in task commits. Capture the helper's branch name.

## Separate Worktree

1. Record the original root, branch, HEAD, and changed paths. If there are uncommitted source changes needed by the plan, resolve their handling with the user first; do not silently drop or copy them. A newly written or modified plan may be copied explicitly.
2. Derive the desired feature name without side effects using `scripts/create-branch.sh --print-name <plan-file>`. Choose a new branch name if it already exists or is checked out. Do not repurpose an existing branch without the user's instruction.
3. Create a new worktree from the current HEAD using `git worktree add -b <new-branch> <worktree-path> HEAD`. Use the client's native worktree feature instead when it supports the required behavior. Do not create/check out a branch in the original working directory first.
4. Locate the plan under the new worktree. Copy only the selected plan if it was untracked or modified; keep its path relative to the project when possible. Carry loaded settings/rules and deliberately configured prompt overrides into the worktree by copying only `.codex/planning.json`, `.codex/planning-rules.md`, and `.codex/exec-plan/` when needed and permitted. Do not copy the whole Codex configuration directory. Do not overwrite different tracked configuration without resolving the difference.
5. Every subsequent shell call and subagent operates in the new worktree; an initial `cd` in one tool call does not change another tool call's directory. Skip `create-branch.sh` in this mode: the branch already exists.
6. Verify that the original checkout's branch, HEAD, and tracked contents still match the recorded state. Report the worktree path and branch to the user. Do not remove the worktree or push automatically at completion.

Worktree operations still respect the client's filesystem permissions. The plugin does not change approval policy or bypass protection of configuration directories.
