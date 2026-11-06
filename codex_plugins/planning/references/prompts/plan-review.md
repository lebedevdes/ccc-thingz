Review an implementation plan before any code is written. Read the attached plan snapshot from PLAN_FILE_PATH, then read the
project's AGENTS.md (if present) and the source files the plan names, so you judge the plan against the
code as it is. Read files using native reading/search tools; shell commands are disabled for this OpenCode process. Do not modify any file.

Report:
- assumptions about existing code that the code contradicts (wrong names, paths, signatures, behavior)
- missing steps that would leave the stated problem unsolved, or changes the plan forgets (callers, tests, docs)
- over-engineering: abstractions, options or layers the stated problem does not need
- task ordering that breaks the build or tests between tasks, and tasks that cannot be tested as written
- conflicts with the project conventions in AGENTS.md or with these custom planning rules: USER_RULES

The plan follows a fixed template (Overview, Context, Development Approach, Testing Strategy, Progress
Tracking, Implementation Steps with checkboxes, Post-Completion). Do not report its required sections,
checkbox format or boilerplate as findings.

Tag each finding with severity:
- CRITICAL: the plan, as written, fails to solve the problem or breaks existing behavior
- MAJOR: a wrong assumption, missing step or design flaw that will cost rework during implementation
- MINOR: clarity, naming, optional simplifications

Format each finding on its own line as: `SEVERITY: <plan section or task> - <description>`.

If nothing found: NO ISSUES FOUND.
