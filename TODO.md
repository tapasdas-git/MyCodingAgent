# Project TODOs

## TASK-040 | completed | P0 | Fix authentication token expiration bug
- Outcome: Refresh tokens automatically 5 minutes before expiration to prevent session drops.
- Depends on: None
- Repository: /path/to/repo
- Harness: primary-name
- Night-ready: yes
- Acceptance:
  - User session remains uninterrupted during active 2-hour window.
  - Unit tests verify silent token refresh trigger.
- Approved by: Alex Mercer
- Approval reference: 2026-07-20 Slack sign-off

## TASK-041 | working | P1 | Add request latency metrics to dashboard
- Outcome: Expose Prometheus metrics for P95 and P99 HTTP request response times.
- Depends on: TASK-040
- Repository: /path/to/repo
- Harness: primary-name
- Acceptance:
  - Metric endpoint `/metrics` exposes `http_request_duration_seconds`.
  - Grafana panel imports metrics cleanly.
- Approved by: Dev Lead
- Approval reference: 2026-07-21 Jira SWAF-041

## TASK-042 | completed | P1 | Implement palindrome utility function
- Outcome: Pure Python function that checks if input string is a valid palindrome, ignoring case and special characters.
- Depends on: None
- Repository: /path/to/repo
- Harness: primary-name
- Night-ready: yes
- Acceptance:
  - Returns `True` for "A man, a plan, a canal: Panama".
  - Returns `False` for "hello world".
  - Unit test suite passes with >= 95% coverage.
- Approved by: Code Reviewer
- Approval reference: 2026-07-22 PR review thread

## TASK-043 | Completed | P2 | Update CLI logging to support JSON output
- Outcome: Allow passing `--format=json` to output structured logs.
- Depends on: None
- Acceptance:
  - Console outputs valid JSON lines when flag is present.
- Approved by: Tech Lead
- Approval reference: 2026-07-23 Arch Sync

## TASK-044 | blocked | P3 | Refactor legacy database connector
- Outcome: Replace deprecated ORM call patterns with async context managers.
- Depends on: TASK-045
- Acceptance:
  - Database pool cleanly releases connections after timeout.
- Approved by: Alex Mercer
- Approval reference: 2026-07-25 Architecture board

## SWAF-045 | Completed | P1 | Implement Fibonacci series utility module
- Outcome: Pure Python module created under `fibonacci/` directory containing sequence generation logic and CLI interface.
- Depends on: None
- Repository: https://github.com/tapasdas-git/MyOmnigent.git
- Harness: primary-name
- Night-ready: yes
- Acceptance:
  - Source files are placed under `fibonacci/` directory (e.g., `fibonacci/__init__.py`, `fibonacci/generator.py`).
  - Test files are placed under `tests/test_fibonacci.py` or `fibonacci/tests/`.
  - Utility function `fibonacci(n: int) -> list[int]` correctly handles edge cases (N=0, N=1, negative inputs).
  - Calling `fibonacci(10)` returns `[0, 1, 1, 2, 3, 5, 8, 13, 21, 34]`.
  - Automated unit test suite passes with 100% code coverage.
- Approved by: Tech Lead
- Approval reference: 2026-07-30 Arch Sync

## SWAF-046 | completed | P1 | Implement palindrome detection utility module
- Outcome: Pure Python module and unit tests for palindrome detection, handling edge cases, case-insensitivity, and special characters.
- Depends on: None
- Repository: https://github.com/tapasdas-git/MyOmnigent.git
- Harness: primary-name
- Night-ready: yes
- Acceptance:
  - Source file created at `palindrome/Coding/checker.py`.
  - Test file created at `palindrome/test/test_checker.py`.
  - Function `is_palindrome(text: str) -> bool` ignores spaces, punctuation, and casing.
  - Returns `True` for "A man, a plan, a canal: Panama".
  - Returns `False` for "Hello World".
  - Unit test suite passes with 100% test coverage.
- Approved by: Tech Lead
- Approval reference: 2026-07-30 Arch Sync

## TASK-046 | completed | P1 | Implement palindrome detection utility module
- Outcome: Pure Python module and unit tests for palindrome detection, handling edge cases, case-insensitivity, and special characters.
- Depends on: None
- Repository: https://github.com/tapasdas-git/MyOmnigent.git
- Harness: primary-name
- Night-ready: yes
- Acceptance:
  - Source file created at `palindrome/Coding/checker.py`.
  - Test file created at `palindrome/test/test_checker.py`.
  - Function `is_palindrome(text: str) -> bool` ignores spaces, punctuation, and casing.
  - Returns `True` for "A man, a plan, a canal: Panama".
  - Returns `False` for "Hello World".
  - Unit test suite passes with 100% test coverage.
- Approved by: Tech Lead
- Approval reference: 2026-07-30 Arch Sync

## TASK-047 | completed | P3 | Create a utility module in `prime_checker` to verify prime numbers and return prime factors.
- Outcome: Pure Python module and unit tests for palindrome detection, handling edge cases, case-insensitivity, and special characters.
- Depends on: None
- Repository: https://github.com/tapasdas-git/MyOmnigent.git
- Harness: primary-name
- Night-ready: yes
Acceptance:
  - Source file created at `prime_checker/Coding/checker.py`.
  - Test file created at `prime_checker/test/test_checker.py`.
  - Function `is_prime(n: int) -> bool` correctly identifies prime numbers (e.g., returns `True` for 7, `False` for 4, and `False` for numbers <= 1).
  - Function `get_prime_factors(n: int) -> list[int]` returns prime factors (e.g., `[2, 3, 3]` for 18).
  - Unit test suite passes with 100% test coverage.
- Approved by: Tech Lead
- Approval reference: 2026-07-30 Arch Sync

## TASK-101 | ready | P1 | [FEATURE] Build Agentic Flight Booking Engine in `workspace/flight_booking_agent/`
- Outcome: Implement a multi-agent flight search and booking engine using Python and Pydantic as a new core feature. Process natural language requests, query flight options, evaluate preferences, and handle booking state validation.
- Depends on: None
- Repository: https://github.com/tapasdas-git/MyCodeAgent.git
- Harness: primary-name
- Night-ready: yes
- Architecture & Tech Stack:
  - Framework: Python 3.11+, Pydantic (v2) for structured schema validations
  - Target Architecture Pattern: ReAct (Routing & Tool-Calling Agent Loop) Pattern. Implement a bounded loop: model decision -> Pydantic-validated tool action -> tool observation -> next decision or final response.
  - ReAct Controls: Define structured Pydantic schemas for model actions and tool observations. Stop safely on a final response, invalid action, tool failure, or configured maximum iteration count.
  - Groq Tool-Calling Protocol: Use Groq native chat-completions tool calling with declared function schemas and `tool_choice="auto"`. Keep per-request message history; append the assistant tool-call message and each matching `role: "tool"` observation with its `tool_call_id`. Support multiple tool calls in one model response.
  - Tool Safety: Use an explicit allowlist of registered tools. Reject unknown tool names, malformed JSON arguments, and schema-invalid arguments without executing a tool.
    1. Search Agent: Queries flight database/mock API.
    2. Preference/Policy Agent: Filters options based on budget, seat preference, and bag policies.
    3. Booking Agent: Handles reservation execution and confirmation generation.
- API Key & Secrets Management:
  - LLM Provider: Use Groq as the runtime LLM provider. Access it through an injectable client/adapter and load `GROQ_API_KEY` dynamically from environment variables.
  - Security Requirement: Fetch keys dynamically via `os.getenv()`. Under no circumstances should API keys be hardcoded in files.
  - Mocking in Tests: Unit tests must use an injected fake Groq/LLM client plus mock objects or fixtures (`pytest.monkeypatch` / `unittest.mock`) so the entire test suite passes offline without active network/API calls.
  - Deterministic Safety: Validate price, inventory, policy, and reservation state in deterministic code before any booking side effect. Protect against duplicate bookings with an idempotency key or equivalent request identity.
  - Booking Authorization: Execute a reservation only after explicit booking authorization in the request or a confirmed booking state. Searching, filtering, or selecting an option must not reserve inventory.
- Workspace Boundary:
  - Source: `workspace/flight_booking_agent/Coding/`
  - Tests: `workspace/flight_booking_agent/test/`
  - Requirements: `workspace/flight_booking_agent/Coding/requirements.txt`
  - Rule: All files and modifications must stay strictly inside `workspace/flight_booking_agent/`. Do not modify root or external repository files.
- Acceptance:
  - Isolated workspace created at `workspace/flight_booking_agent/`.
  - Source files created under `workspace/flight_booking_agent/Coding/`:
    - `requirements.txt`: Local dependencies (`pydantic>=2.0.0`, `groq`, `pytest`).
    - `schemas.py`: Pydantic models for `FlightQuery`, `FlightOption`, and `BookingConfirmation`.
    - `tools.py`: Mock Flight Search API and Mock Reservation Gateway.
    - `agents.py`: Groq client/adapter boundary, Search Agent, Preference/Policy Agent, Booking Agent, and ReAct Supervisor Orchestrator.
  - Test files created under `workspace/flight_booking_agent/test/`:
    - `test_flight_search.py`: Verifies intent parsing, fake-LLM tool routing, ReAct action/observation handling, and flight filtering.
    - `test_booking_flow.py`: Verifies end-to-end multi-agent orchestration, booking idempotency, failure/budget/inventory edge cases, malformed model actions, and loop-limit handling.
    - `test_react_protocol.py`: Verifies native tool-schema registration, assistant/tool message ordering, matching `tool_call_id` values, multiple tool calls, unknown-tool rejection, malformed arguments, and loop-limit termination.
  - Test suite passes with 100% pass rate locally.
- Approved by: Tech Lead
- Approval reference: 2026-08-01 Arch Sync
