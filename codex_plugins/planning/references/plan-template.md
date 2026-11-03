# Plan Template

Use the original planning template below. Number every task with concrete sequential integers.

```markdown
# [Plan Title]

## Overview
- clear description of the feature/change being implemented
- problem it solves and key benefits
- how it integrates with existing system

## Context (from discovery)
- files/components involved: [list from step 0]
- related patterns found: [patterns discovered]
- dependencies identified: [dependencies]

## Development Approach
- **testing approach**: [TDD / Regular - from user preference in planning]
- complete each task fully before moving to the next
- make small, focused changes
- **CRITICAL: every task MUST include new/updated tests** for code changes in that task
  - tests are not optional - they are a required part of the checklist
  - write unit tests for new functions/methods
  - write unit tests for modified functions/methods
  - add new test cases for new code paths
  - update existing test cases if behavior changes
  - tests cover both success and error scenarios
- **CRITICAL: all tests must pass before starting next task** - no exceptions
- **CRITICAL: update this plan file when scope changes during implementation**
- run tests after each change
- maintain backward compatibility

## Testing Strategy
- **unit tests**: required for every task (see Development Approach above)
- **e2e tests**: if project has UI-based e2e tests (Playwright, Cypress, etc.):
  - UI changes → add/update e2e tests in same task as UI code
  - backend changes supporting UI → add/update e2e tests in same task
  - treat e2e tests with same rigor as unit tests (must pass before next task)
  - store e2e tests alongside unit tests (or in designated e2e directory)
  - example: if task implements new form field, add e2e test checking form submission

## Progress Tracking
- mark completed items with `[x]` immediately when done
- add newly discovered tasks with ➕ prefix
- document issues/blockers with ⚠️ prefix
- update plan if implementation deviates from original scope
- keep plan in sync with actual work done

## Solution Overview
- high-level approach and architecture chosen
- key design decisions and rationale
- how it fits into the existing system

## Technical Details
- data structures and changes
- parameters and formats
- processing flow

## What Goes Where
- **Implementation Steps** (`[ ]` checkboxes): tasks achievable within this codebase - code changes, tests, documentation updates
- **Post-Completion** (no checkboxes): items requiring external action - manual testing, changes in consuming projects, deployment configs, third-party verifications

## Implementation Steps

<!--
Task structure guidelines:
- Each task = ONE logical unit (one function, one endpoint, one component)
- Use specific descriptive names, not generic "[Core Logic]" or "[Implementation]"
- Each task MUST have a **Files:** block listing files to Create/Modify (before checkboxes)
- Aim for ~5 checkboxes per task (more is OK if logically atomic)
- **CRITICAL: number ALL tasks with concrete sequential integers** - the two trailing tasks below are shown as "Task N-1" and "Task N" where N is a PLACEHOLDER for the total task count, NOT literal text. Substitute real numbers continuing the sequence from your last implementation task (e.g. with 14 implementation tasks they become "Task 15: Verify acceptance criteria" and "Task 16: ... Update documentation"). NEVER write the literal strings "Task N-1" or "Task N" into the plan.
- **CRITICAL: Each task MUST end with writing/updating tests before moving to next**
  - tests are not optional - they are a required deliverable of every task
  - write tests for all NEW code added in this task
  - write tests for all MODIFIED code in this task
  - include both success and error scenarios in tests
  - list tests as SEPARATE checklist items, not bundled with implementation

Example (NOTICE: Files block + tests as separate checklist items):

### Task 1: Add password hashing utility

**Files:**
- Create: `src/auth/hash`
- Create: `src/auth/hash_test`

- [ ] create `src/auth/hash` with HashPassword and VerifyPassword functions
- [ ] implement bcrypt-based hashing with configurable cost
- [ ] write tests for HashPassword (success + error cases)
- [ ] write tests for VerifyPassword (success + error cases)
- [ ] run tests - must pass before task 2

### Task 2: Add user registration endpoint

**Files:**
- Create: `src/api/users`
- Modify: `src/api/router`
- Create: `src/api/users_test`

- [ ] create `POST /api/users` handler in `src/api/users`
- [ ] add input validation (email format, password strength)
- [ ] integrate with password hashing utility
- [ ] write tests for handler success case with table-driven cases
- [ ] write tests for handler error cases (invalid input, missing fields)
- [ ] run tests - must pass before task 3
-->

### Task 1: [specific name - what this task accomplishes]

**Files:**
- Create: `exact/path/to/new_file`
- Modify: `exact/path/to/existing`

- [ ] [specific action with file reference - code implementation]
- [ ] [specific action with file reference - code implementation]
- [ ] write tests for new/changed functionality (success cases)
- [ ] write tests for error/edge cases
- [ ] run tests - must pass before next task

<!-- replace "N-1" and "N" below with the actual next sequential numbers continuing from your last implementation task - do NOT emit the literal letter N -->
### Task N-1: Verify acceptance criteria
- [ ] verify all requirements from Overview are implemented
- [ ] verify edge cases are handled
- [ ] run full test suite: `<project test command>`
- [ ] run e2e tests if project has them: `<project e2e test command>`
- [ ] verify test coverage meets project standard

### Task N: [Final] Update documentation
- [ ] update README.md if needed
- [ ] update AGENTS.md if new patterns discovered
- [ ] move this plan to `docs/plans/completed/`

## Post-Completion
*Items requiring manual intervention or external systems - no checkboxes, informational only*

**Manual verification** (if applicable):
- manual UI/UX testing scenarios
- performance testing under load
- security review considerations

**External system updates** (if applicable):
- consuming projects that need updates after this library change
- configuration changes in deployment systems
- third-party service integrations to verify
```
