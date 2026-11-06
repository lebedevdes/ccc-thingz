# Custom Rules for Brainstorm

Rules are free-form Markdown applied to the brainstorm dialogue alongside the skill's built-in instructions.

## Locations and Precedence

1. **Project:** `.codex/brainstorm-rules.md` relative to the project root.
2. **User:** `${CODEX_HOME:-$HOME/.codex}/brainstorm-rules.md`.

The first non-empty file wins. Empty files are treated as absent, and rules are never merged. The user file lives outside the installed plugin cache, so plugin updates do not replace it.

The bundled `../scripts/resolve-rules.sh` takes a filename and an optional user directory. Resolve its absolute path from this skill's directory and run it from the project root. It prints the selected file's contents, or nothing if neither file contains rules.

## Managing Rules

- **Show rules:** run the resolver and display the result. Check whether the project file is non-empty to identify the source; otherwise a non-empty result came from the user file. Report when neither contains rules.
- **Add/update project rules:** create or edit `.codex/brainstorm-rules.md`.
- **Add/update user rules:** resolve `CODEX_HOME` (default `$HOME/.codex`) and create or edit `brainstorm-rules.md` there. Respect the client's filesystem permissions; if writing there is unavailable, explain the limitation and offer project rules.
- **Clear project/user rules:** remove only the requested rules file, respecting the client's permissions.

Preserve unrelated rules when adding a preference. Ask which level to change if the user's request does not make the destination clear. These operations manage preferences; they do not edit the installed plugin.

## Example

```markdown
## Design preferences
- Prefer simple solutions over clever abstractions.
- Consider backward compatibility.

## Technology constraints
- Backend uses Go with the standard library where possible.
- Frontend uses HTMX.
```
