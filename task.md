# Task Backlog

Add each task as a separate section using the format below. Task IDs must be
unique and use `TASK-` followed by digits, for example `TASK-001`.

## TASK-001 — Palinndrom

### Summary

write a palinndrom of words

### Scope

- Add a small word-palindrome helper in `palinndrom.py`.
- Add unit tests that cover the helper's behavior.
- Keep the change self-contained; do not modify unrelated tasks or features.

### Acceptance criteria

- [ ] Calling the helper with `["red", "blue", "green"]` returns `["red", "blue", "green", "blue", "red"]`.
- [ ] Empty input returns an empty list, and a single word returns that word unchanged.
- [ ] The helper preserves the original words, does not mutate the caller's input, and accepts any iterable of strings.
- [ ] `python -m unittest` passes.

### Constraints

- Pure standard-library Python only; no new runtime dependencies.
- Behavior must remain compatible with the existing Python test style in this repo.

### Notes

Optional implementation context, links, or background information.

## TASK-002 — Another task title

### Summary

Describe a separate task here.

### Scope

- List the intended scope.

### Acceptance criteria

- [ ] Define the required outcome.

### Constraints

- Add applicable constraints, or write `None`.
