# 🛡️ Code Review Guidelines & Guardrails

Approve a task change only when every requirement below passes:

- The implementation satisfies the acceptance criteria in `TODO.md`.
- The diff is focused; it contains no unrelated, generated, or credential files.
- Code is readable, maintainable, and consistent with the repository's existing style.
- Errors, edge cases, and input validation are handled where the task requires them.
- Relevant automated tests are added or updated, and the reviewer has run them successfully.
- No secrets, tokens, passwords, private keys, or sensitive data are introduced.

Return exactly `APPROVED` only when every item passes. Otherwise return `CHANGES_REQUESTED` with specific, actionable findings[cite: 3].

---

## 1. Directory Structure & Scope Rules

* **Task Isolation**: All new application code and tests for a task must reside inside a dedicated top-level task directory (e.g., `fibonacci/` or `palindrome/`).
* **Subdirectory Placement**:
  * Application/module logic **must** be placed in `<task_directory>/Coding/`.
  * Unit tests and test fixtures **must** be placed in `<task_directory>/test/`.
* **Clean Root Directory**: No loose `.py` files, temporary scripts, or test logs may be created directly in the repository root directory.
* **Scope Control**: Pull requests must only contain changes relevant to the target task ID and `CHANGELOG.md`[cite: 3]. Unrelated refactoring, generated files, or extra feature implementations are strictly forbidden[cite: 3].

---

## 2. Code Quality & Syntax Standards (Python)

* **Type Annotations**: All public functions, methods, and module outputs must include explicit Python type hints (PEP 484).
  ```python
  # Preferred
  def is_palindrome(text: str) -> bool: ...