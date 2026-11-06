Review code changes. Read the complete attached current Git change snapshot. The runner includes committed fixes and tracked working changes on every iteration. Read source files for context. Read the attached plan snapshot from PLAN_FILE_PATH to understand the intent before evaluating findings — this lets you distinguish intentional design decisions from real defects. Read the attached progress snapshot from PROGRESS_FILE_PATH for context on previous review iterations and fixes — re-evaluate all findings independently, previous fixes may be incomplete or wrong. Check for: bugs, security issues, race conditions, error handling, code quality. Use native reading/search tools; do not edit files, run shell commands, ask questions, or delegate.

Additional custom rules:
USER_RULES

Tag each finding with severity:
- CRITICAL: bugs causing crashes, data loss, security holes, race conditions
- MAJOR: real correctness issues — incorrect behavior, missing error handling, broken contracts
- MINOR: style, documentation drift, doc/code inconsistencies, nits, optional improvements

Format each finding on its own line as: `SEVERITY: file:line - description`.

If nothing found: NO ISSUES FOUND.
