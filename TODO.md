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

## TASK-041 | completed | P1 | Add request latency metrics to dashboard
- Outcome: Expose Prometheus metrics for P95 and P99 HTTP request response times.
- Depends on: TASK-040
- Repository: /path/to/repo
- Harness: primary-name
- Acceptance:
  - Metric endpoint `/metrics` exposes `http_request_duration_seconds`.
  - Grafana panel imports metrics cleanly.
- Approved by: Dev Lead
- Approval reference: 2026-07-21 Jira SWAF-041

## TASK-042 | completed | Feature | Implement palindrome utility function
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
- Repository: https://github.com/tapasdas-git/MyCodingAgent.git
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

## TASK-107 | completed | P2 | [FEATURE] Implement Palindrome Detection Utility Module in `workspace/palindrome_util/`
- Outcome: Implement a lightweight, high-performance palindrome detection utility module supporting multi-language string normalization, numerical/phrase checking, and Pydantic schema validation for metadata reporting.
- Depends on: None
- Repository: https://github.com/tapasdas-git/MyCodingAgent.git
- Harness: primary-name
- Night-ready: yes
- Architecture & Tech Stack:
  - Framework: Python 3.11+, Pydantic (v2)
  - Pattern: Utility Module Pattern
    1. PalindromeChecker: Core engine supporting strict checking, case-insensitive/ignore-punctuation checking, and numeric range filtering.
    2. Schemas: Pydantic models for input validation (`PalindromeRequest`) and output analysis (`PalindromeResponse` with metadata like cleaned string, length, and boolean result).
- API Key & Secrets Management:
  - Security Requirement: No network calls or API keys required for this local utility module.
- Workspace Boundary:
  - Source: `workspace/palindrome_util/Coding/`
  - Tests: `workspace/palindrome_util/test/`
  - Requirements: `workspace/palindrome_util/Coding/requirements.txt`
  - Rule: All generated files must stay strictly inside `workspace/palindrome_util/`. Do not edit files outside this directory.
- Acceptance:
  - Isolated workspace directory created at `workspace/palindrome_util/`.
  - Source files created under `workspace/palindrome_util/Coding/`:
    - `requirements.txt`: Local dependencies (`pydantic>=2.0.0`, `pytest`).
    - `schemas.py`: Pydantic models for `PalindromeRequest` and `PalindromeResponse`.
    - `checker.py`: Core implementation of `PalindromeChecker` class with normalization logic.
  - Test files created under `workspace/palindrome_util/test/`:
    - `test_checker.py`: Verifies phrase palindromes (e.g., "A man, a plan, a canal: Panama"), single-character/empty string edge cases, non-palindromes, and numeric inputs.
  - Test suite passes with 100% pass rate locally.
- Approved by: Tech Lead
- Approval reference: 2026-08-06 Arch Sync

## TASK-046 | completed | P1 | Implement palindrome detection utility module
- Outcome: Pure Python module and unit tests for palindrome detection, handling edge cases, case-insensitivity, and special characters.
- Depends on: None
- Repository: https://github.com/tapasdas-git/MyCodingAgent.git
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
- Repository: https://github.com/tapasdas-git/MyCodingAgent.git
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

## TASK-101 | completed | P1 | [FEATURE] Build Agentic Flight Booking Engine in `workspace/flight_booking_agent/`
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
## TASK-109 | APPROVED | P2 | [FEATURE] Implement Event-Driven Audit Logger Module in `workspace/audit_log/`
- Outcome: Implement a thread-safe audit logging framework using the Observer Pattern to capture system events, calculate SHA-256 integrity checksums, and serialize structured audit records with Pydantic validation.
- Depends on: None
- Repository: https://github.com/tapasdas-git/MyCodingAgent.git
- Harness: primary-name
- Night-ready: yes
- Architecture & Tech Stack:
  - Framework: Python 3.11+, Pydantic (v2)
  - Pattern: Observer / Event-Dispatcher Pattern
    1. EventPublisher: Central channel where application components publish audit events (e.g., USER_LOGIN, FILE_ACCESS, CONFIG_CHANGE).
    2. FileAuditObserver & MemoryAuditObserver: Observers that validate payloads, generate cryptographic checksums, and log event metrics.
    3. Schemas: Pydantic models for `AuditEvent` (input event) and `AuditLogRecord` (validated log entry with hash signature and timestamp).
- API Key & Secrets Management:
  - Security Requirement: No network calls or hardcoded secrets required. Use mock parameters for offline execution.
- Workspace Boundary:
  - Source: `workspace/audit_log/Coding/`
  - Tests: `workspace/audit_log/test/`
  - Requirements: `workspace/audit_log/Coding/requirements.txt`
  - Rule: All generated files must stay strictly inside `workspace/audit_log/`. Do not edit files outside this directory.
- Acceptance:
  - Isolated workspace directory created at `workspace/audit_log/`.
  - Source files created under `workspace/audit_log/Coding/`:
    - `requirements.txt`: Local dependencies (`pydantic>=2.0.0`, `pytest`).
    - `schemas.py`: Pydantic schema models for `AuditEvent` and `AuditLogRecord`.
    - `publisher.py`: Implementation of `EventPublisher` supporting dynamic observer registration and event dispatching.
    - `observers.py`: Implementation of `FileAuditObserver` and `MemoryAuditObserver`.
  - Test files created under `workspace/audit_log/test/`:
    - `test_logger.py`: Verifies observer registration, payload schema validation, tamper detection via checksum calculation, and multi-observer notification loops.
  - Test suite passes with 100% pass rate locally.
- Approved by: Tech Lead
- Approval reference: 2026-08-06 Arch Sync
## TASK-110 | APPROVED | P2 | [FEATURE] Implement In-Memory Product Inventory CRUD Engine in `workspace/inventory_crud/`
- Outcome: Build an in-memory Product Inventory Management Service implementing complete CRUD operations, fuzzy search, soft deletion, and Pydantic schema validation.
- Depends on: None
- Repository: https://github.com/tapasdas-git/MyCodingAgent.git
- Harness: primary-name
- Night-ready: yes
- Architecture & Tech Stack:
  - Framework: Python 3.11+, Pydantic (v2)
  - Pattern: Repository / In-Memory Store Pattern
    1. InventoryRepository: Thread-safe storage engine supporting Create, Read (by ID and query filter), Update (partial & full), and Soft/Hard Delete.
    2. Schemas: Pydantic models for product creation (`ProductCreate`), updates (`ProductUpdate`), response formatting (`ProductResponse`), and search filtering (`ProductFilter`).
- API Key & Secrets Management:
  - Security Requirement: No external network calls or API keys required. Execution remains entirely local.
- Workspace Boundary:
  - Source: `workspace/inventory_crud/Coding/`
  - Tests: `workspace/inventory_crud/test/`
  - Requirements: `workspace/inventory_crud/Coding/requirements.txt`
  - Rule: All generated files must stay strictly inside `workspace/inventory_crud/`. Do not edit files outside this directory.
- Acceptance:
  - Isolated workspace directory created at `workspace/inventory_crud/`.
  - Source files created under `workspace/inventory_crud/Coding/`:
    - `requirements.txt`: Local dependencies (`pydantic>=2.0.0`, `pytest`).
    - `schemas.py`: Pydantic models with field constraints (e.g., price > 0, stock >= 0).
    - `repository.py`: Core `InventoryRepository` class with methods: `create_product`, `get_product_by_id`, `list_products`, `update_product`, and `delete_product`.
    - `exceptions.py`: Custom exceptions (`ProductNotFoundError`, `DuplicateSKUError`).
  - Test files created under `workspace/inventory_crud/test/`:
    - `test_crud.py`: Verifies all CRUD lifecycle operations, duplicate SKU rejection, partial payload updates, soft deletion filtering, and missing entity handling.
  - Test suite passes with 100% pass rate locally.
- Approved by: Tech Lead
- Approval reference: 2026-08-07 Arch Sync
## TASK-111 | delivered | P2 | [FEATURE] Implement Token Bucket Rate Limiter in `workspace/rate_limiter/`
- Outcome: Implement an in-memory Rate Limiter service utilizing the Token Bucket algorithm with configurable bucket capacities, refill rates, and Pydantic schema validation.
- Depends on: None
- Repository: https://github.com/tapasdas-git/MyCodingAgent.git
- Harness: primary-name
- Night-ready: yes
- Architecture & Tech Stack:
  - Framework: Python 3.11+, Pydantic (v2)
  - Pattern: State Pattern / Token Bucket Algorithm
    1. TokenBucket: Manages token replenishment dynamically based on elapsed time and consumption requests per client/key.
    2. RateLimiterService: Multi-tenant rate limiter coordinating per-client buckets with status reporting.
    3. Schemas: Pydantic models for request consumption (`RateLimitRequest`), status response (`RateLimitResult`), and bucket configuration (`BucketConfig`).
- API Key & Secrets Management:
  - Security Requirement: No network calls or API keys required. Execution remains entirely local.
- Workspace Boundary:
  - Source: `workspace/rate_limiter/Coding/`
  - Tests: `workspace/rate_limiter/test/`
  - Requirements: `workspace/rate_limiter/Coding/requirements.txt`
  - Rule: All generated files must stay strictly inside `workspace/rate_limiter/`. Do not edit files outside this directory.
- Acceptance:
  - Isolated workspace directory created at `workspace/rate_limiter/`.
  - Source files created under `workspace/rate_limiter/Coding/`:
    - `requirements.txt`: Local dependencies (`pydantic>=2.0.0`, `pytest`).
    - `schemas.py`: Pydantic models for `BucketConfig`, `RateLimitRequest`, and `RateLimitResult`.
    - `limiter.py`: Implementation of `TokenBucket` class and `RateLimiterService` supporting token consumption (`allow_request`) and status metrics.
  - Test files created under `workspace/rate_limiter/test/`:
    - `test_limiter.py`: Verifies burst request handling, bucket exhaustion (blocking requests), time-based token refill mechanisms, and isolated multi-client tracking.
  - Test suite passes with 100% pass rate locally.
- Approved by: Tech Lead
- Approval reference: 2026-08-07 Arch Sync
## TASK-112 | PR creation complete | P2 | [FEATURE] Implement Async Web Content Fetcher Module in `workspace/async_crawler/`
- Outcome: Implement an asynchronous, concurrency-limited HTTP content fetcher capable of retrieving raw text/HTML, enforcing independent per-host concurrency limits, retrying transient failures with exponential backoff, and returning Pydantic-validated results.
- Depends on: None
- Repository: https://github.com/tapasdas-git/MyCodingAgent.git
- Harness: primary-name
- Night-ready: yes
- Architecture & Tech Stack:
  - Framework: Python 3.11+, asyncio, httpx, Pydantic (v2)
  - Pattern: Async Worker Queue / Semaphore Pattern
    1. AsyncFetcher: Core engine using one reusable `httpx.AsyncClient` during its async context and a separately keyed `asyncio.Semaphore` per normalized host.
    2. Schemas: Pydantic models for `CrawlRequest`, `CrawlResult`, and fetcher configuration including positive concurrency, timeout, retry-count, and backoff constraints.
    3. Resilience: Deterministic exponential backoff for `429`, `502`, `503`, and `504`; non-retryable HTTP responses fail immediately.
    4. Testability: Time delay and HTTP transport behavior must be injectable or mockable so tests never make real network calls or wait for real backoff intervals.
- API Key & Secrets Management:
  - Security Requirement: No hardcoded credentials or target endpoints. Accept only validated `http` and `https` request URLs; tests must use injected or mocked transports and remain fully offline.
- Workspace Boundary:
  - Source: `workspace/async_crawler/Coding/`
  - Tests: `workspace/async_crawler/test/`
  - Requirements: `workspace/async_crawler/Coding/requirements.txt`
  - Rule: All generated files must stay strictly inside `workspace/async_crawler/`. Do not edit files outside this directory.
- Implementation Guardrails:
  - Use `httpx.AsyncClient` through an asynchronous context manager and close it deterministically.
  - Enforce `max_concurrent_requests` independently per normalized host rather than through one global semaphore.
  - Retry only `429`, `502`, `503`, and `504` up to configured `max_retries` (default `3`) using exponential backoff; define whether `max_retries` counts retries after the initial request.
  - Raise `CrawlTimeoutError` for request timeouts and `CrawlFetchError` after retry exhaustion or for non-retryable HTTP failures such as `401` and `404`.
  - Preserve cancellation by re-raising `asyncio.CancelledError`; do not convert cancellation into a domain failure.
  - Validate all configuration, request, and result objects with Pydantic v2 models; do not return unvalidated dictionaries or untyped tuples.
  - Fully type all public function and method signatures. Do not use bare exception handlers or swallow unexpected failures.
  - Declare `httpx>=0.24.0`, `pydantic>=2.0.0`, `pytest`, and `pytest-asyncio` in `requirements.txt`.
- Acceptance:
  - Isolated workspace created at `workspace/async_crawler/`.
  - Source files created under `workspace/async_crawler/Coding/`:
    - `requirements.txt`: Contains all task runtime and test dependencies.
    - `schemas.py`: Defines validated `CrawlRequest`, `CrawlResult`, and fetcher configuration models.
    - `exceptions.py`: Custom `CrawlFetchError` and `CrawlTimeoutError`.
    - `fetcher.py`: Implements `AsyncFetcher` with per-host semaphore locking, deterministic client lifecycle, timeout handling, and exponential-backoff retries.
  - Test files created under `workspace/async_crawler/test/`:
    - `test_fetcher.py`: Uses pytest-asyncio and mocked or injected HTTP behavior to verify successful fetches, independent per-host concurrency limits, retry counts and backoff progression, retry exhaustion, immediate non-retryable failures, timeouts, cancellation propagation, schema validation, and client cleanup without real network calls.
  - All tests pass locally with zero real network access using `pytest workspace/async_crawler/test/`.
- Approved by: Tech Lead
- Approval reference: 2026-08-07 Arch Sync
## TASK-113 | PR creation complete | P2 | [FEATURE] Implement Async Priority Task Scheduler Module in `workspace/priority_scheduler/`
- Outcome: Implement an asynchronous, priority-aware task scheduling utility capable of processing jobs based on priority levels, enforcing global and per-category concurrency limits, handling worker retries with backoff, and returning Pydantic-validated execution summaries.
- Depends on: None
- Repository: https://github.com/tapasdas-git/MyCodingAgent.git
- Harness: primary-name
- Night-ready: yes
- Architecture & Tech Stack:
  - Framework: Python 3.11+, asyncio, Pydantic (v2)
  - Pattern: Priority Queue / Producer-Consumer Worker Pattern
    1. PriorityScheduler: Core engine utilizing an `asyncio.PriorityQueue` to route jobs based on numerical priority, managed by a bounded pool of asynchronous worker tasks.
    2. Schemas: Pydantic models for `TaskJob`, `TaskResult`, and scheduler configuration enforcing valid priority bounds, retry counts, execution timeouts, and queue size limits.
    3. Resilience: Configurable max retries per task for transient failures with backoff; failed tasks transition to a terminal error state upon retry exhaustion.
    4. Testability: Execution clocks and async delays must be mockable/injectable so tests never depend on wall-clock time or real sleep delays.
- API Key & Secrets Management:
  - Security Requirement: No network credentials or external state dependencies. All execution logic operates strictly in-memory; tests must execute entirely offline.
- Workspace Boundary:
  - Source: `workspace/priority_scheduler/Coding/`
  - Tests: `workspace/priority_scheduler/test/`
  - Requirements: `workspace/priority_scheduler/Coding/requirements.txt`
  - Rule: All generated files must stay strictly inside `workspace/priority_scheduler/`. Do not edit files outside this directory.
- Implementation Guardrails:
  - Manage worker task lifecycles cleanly within an asynchronous context manager (`async with`) and ensure graceful shutdown of all background consumers upon exit.
  - Enforce worker pool limits via worker pool count and category-level execution limits using isolated `asyncio.Semaphore` instances.
  - Process higher-priority tasks ahead of lower-priority ones, retaining FIFO ordering within identical priority levels.
  - Raise `TaskTimeoutError` when task execution exceeds its specified time budget and `TaskExecutionError` after retry exhaustion or unhandled task exceptions.
  - Preserve cancellation by re-raising `asyncio.CancelledError`; do not absorb worker cancellation into generic domain errors.
  - Validate all job definitions, queue payloads, and execution results using Pydantic v2 models; do not accept or return untyped dicts.
  - Fully type-annotate all public classes, signatures, and async generators. Do not use bare `except:` blocks or swallow unexpected errors.
  - Declare `pydantic>=2.0.0`, `pytest`, and `pytest-asyncio` in `requirements.txt`.
- Acceptance:
  - Isolated workspace created at `workspace/priority_scheduler/`.
  - Source files created under `workspace/priority_scheduler/Coding/`:
    - `requirements.txt`: Contains runtime and test dependencies.
    - `schemas.py`: Defines validated `TaskJob`, `TaskResult`, and scheduler configuration models.
    - `exceptions.py`: Custom `TaskExecutionError` and `TaskTimeoutError`.
    - `scheduler.py`: Implements `PriorityScheduler` with worker pool lifecycle, priority queue consumption, category semaphores, and retry logic.
  - Test files created under `workspace/priority_scheduler/test/`:
    - `test_scheduler.py`: Uses `pytest-asyncio` to verify priority ordering, concurrency throttling, retry exhaustion, task timeout enforcement, cancellation safety, context-manager cleanup, and schema validation.
  - All tests pass locally with zero external dependencies using `pytest workspace/priority_scheduler/test/`.
- Approved by: Tech Lead
- Approval reference: 2026-08-07 Arch Sync
## TASK-116 | APPROVED | P2 | [FEATURE] Add greeting service in `workspace/greeting_service/`
- Outcome: Provide a typed greeting function with deterministic unit tests.
- Depends on: None
- Repository: https://github.com/your-account/MyCodingAgent.git
- Architecture & Tech Stack:
  - Python 3.11+ with pytest.
- API Key & Secrets Management:
  - No network calls or secrets are required.
- Workspace Boundary:
  - Source: `workspace/greeting_service/Coding/`
  - Tests: `workspace/greeting_service/test/`
  - Requirements: `workspace/greeting_service/Coding/requirements.txt`
  - Rule: Do not modify files outside `workspace/greeting_service/`.
- Acceptance:
  - `workspace/greeting_service/Coding/service.py` defines `greet(name: str) -> str`.
  - `workspace/greeting_service/Coding/requirements.txt` exists.
  - `workspace/greeting_service/test/test_service.py` covers valid and invalid input.
  - The task pytest suite passes locally.
- Approved by: Tech Lead
- Approval reference: Example approval
## TASK-117 | PR creation complete | P2 | [FEATURE] Add greeting service in `workspace/greeting_service/`
- Outcome: Provide a typed greeting function with deterministic unit tests.
- Depends on: None
- Repository: https://github.com/your-account/MyCodingAgent.git
- Architecture & Tech Stack:
  - Python 3.11+ with pytest.
- API Key & Secrets Management:
  - No network calls or secrets are required.
- Workspace Boundary:
  - Source: `workspace/greeting_service/Coding/`
  - Tests: `workspace/greeting_service/test/`
  - Requirements: `workspace/greeting_service/Coding/requirements.txt`
  - Rule: Do not modify files outside `workspace/greeting_service/`.
- Acceptance:
  - `workspace/greeting_service/Coding/service.py` defines `greet(name: str) -> str`.
  - `workspace/greeting_service/Coding/requirements.txt` exists.
  - `workspace/greeting_service/test/test_service.py` covers valid and invalid input.
  - The task pytest suite passes locally.
- Approved by: Tech Lead
- Approval reference: Example approval
## TASK-118 | APPROVED | P2 | [FEATURE] Add greeting service in `workspace/greeting_service/`
- Outcome: Provide a typed greeting function with deterministic unit tests.
- Depends on: None
- Repository: https://github.com/your-account/MyCodingAgent.git
- Architecture & Tech Stack:
  - Python 3.11+ with pytest.
- API Key & Secrets Management:
  - No network calls or secrets are required.
- Workspace Boundary:
  - Source: `workspace/greeting_service/Coding/`
  - Tests: `workspace/greeting_service/test/`
  - Requirements: `workspace/greeting_service/Coding/requirements.txt`
  - Rule: Do not modify files outside `workspace/greeting_service/`.
- Acceptance:
  - `workspace/greeting_service/Coding/service.py` defines `greet(name: str) -> str`.
  - `workspace/greeting_service/Coding/requirements.txt` exists.
  - `workspace/greeting_service/test/test_service.py` covers valid and invalid input.
  - The task pytest suite passes locally.
- Approved by: Tech Lead
- Approval reference: Example approval
## TASK-121 | PR creation complete | P2 | [FEATURE] Add greeting service in `workspace/greeting_service/`
- Outcome: Provide a typed greeting function with deterministic unit tests.
- Depends on: None
- Repository: https://github.com/tapasdas-git/MyCodingAgent.git
- Architecture & Tech Stack:
  - Python 3.11+ with pytest.
- Acceptance:
  - `workspace/greeting_service/Coding/service.py` defines `greet(name: str) -> str`.
  - `workspace/greeting_service/test/test_service.py` covers valid and invalid input.
  - The task pytest suite passes locally.