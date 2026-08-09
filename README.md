# MyCodeAgent

MyCodeAgent turns an approved task in `TODO.md` into an isolated implementation,
tests it, reviews it, and—when explicitly authorized—commits the result, pushes a
feature branch, and opens a GitHub pull request.

The workflow is hierarchical:

- A Supervisor LLM observes the current execution memory and selects one legal
  next action.
- Explorer, Implementer, Test Writer, and Reviewer agents perform bounded,
  role-specific work through Omnigent.
- Deterministic Python code owns state transitions, workspace isolation,
  validation, pytest execution, fingerprints, the five-cycle limit, delivery,
  logging, and cleanup.

MyCodeAgent creates pull requests; it does not merge them.

## Quick start: task to pull request

### 1. Prerequisites

Install or configure:

- Python 3.11 or newer
- Git, with an `origin` remote and an accessible `origin/main`
- [GitHub CLI](https://cli.github.com/) authenticated for the target repository
- Omnigent, with the configured LLM harness authenticated
- `pytest` for MyCodeAgent's own control-plane tests

Confirm the external tools before starting:

```bash
python3 --version
git --version
command -v omnigent
gh auth status
git remote -v
```

On native Windows, run the equivalent checks from PowerShell:

```powershell
py -3 --version
git --version
Get-Command omnigent
gh auth status
git remote -v
```

If the compatible Omnigent executable is not named `omnigent`, set its path:

```bash
export MYCODEAGENT_OMNIGENT_EXECUTABLE=/absolute/path/to/omnigent
```

PowerShell equivalent:

```powershell
$env:MYCODEAGENT_OMNIGENT_EXECUTABLE = "C:\Tools\Omnigent\omnigent.exe"
```

### 2. Install MyCodeAgent

Run these commands from the repository root:

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install -e .
python -m pip install pytest
python -m pytest -q -p no:cacheprovider
```

On native Windows PowerShell, use:

```powershell
py -3 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -e .
python -m pip install pytest
python -m pytest -q -p no:cacheprovider
```

If PowerShell prevents activation, the virtual environment can be used without
changing the execution policy:

```powershell
.\venv\Scripts\python.exe -m pip install -e .
.\venv\Scripts\python.exe -m pip install pytest
.\venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
```

The current control-plane suite contains 44 tests, including one native-Windows
path-separator test. Non-Windows runs report `43 passed, 1 skipped`; a successful
native Windows run should execute all 44 tests.

### 3. Add a ready task to `TODO.md`

Use a unique task ID and declare explicit source and test boundaries. Both
directories must share the same `workspace/<task-name>/` root.

```markdown
## TASK-113 | ready | P2 | [FEATURE] Add greeting service in `workspace/greeting_service/`
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
```

The task parser requires:

- A heading in the form `## TASK-ID | state | priority | title`.
- A state of `ready` or `RECEIVED` for automatic selection.
- At least one item under `Acceptance`.
- Safe relative paths under `workspace/`.
- Source and test paths inside the same task workspace root.

Backticked filenames in the task are treated as required artifacts, so keep
their names and paths accurate.

Task workspace paths are portable repository-relative identifiers. Use forward
slashes such as `workspace/greeting_service/Coding/` in `TODO.md` on every
operating system, including Windows. Physical paths such as the repository and
worktree locations are converted to native paths by MyCodeAgent.

### 4. Validate the normalized task

Before invoking an LLM, inspect what MyCodeAgent parsed:

```bash
mycodeagent show-task TASK-113
```

Check the task ID, repository, acceptance criteria, workspace boundary, and
`required_files` in the JSON output. Correct `TODO.md` before continuing if any
value is wrong.

### 5. Run the complete delivery workflow

```bash
mycodeagent run TASK-113 --deliver
```

This is the recommended command for an explicit task-to-PR test. `--deliver`
authorizes remote Git actions only after validation, tests, and review succeed.
It does not bypass any quality gate.

To process the first `ready`/`RECEIVED` task instead, use:

```bash
mycodeagent submit --deliver
```

`submit TASK-113 --deliver` is also accepted, but `run TASK-113 --deliver` is
clearer when testing one specific task.

### 6. Monitor the run

In another terminal, follow the task-level trace:

```bash
tail -f logs/TASK-113.logs
```

Inspect the latest persisted task state at any time:

```bash
mycodeagent status TASK-113
```

The final CLI result is JSON similar to:

```json
{
  "run_id": "task-113-0123456789ab",
  "state": "delivered",
  "cycles": 1,
  "worktree": "/path/to/CodedWorkspace/MyCodingAgent/task-113"
}
```

After delivery, confirm the PR and worktree cleanup:

```bash
gh pr list --head feature/task-113
git worktree list
```

The output records the worktree used during execution even when that directory
has subsequently been removed by successful cleanup.

## What happens during a run

```text
TODO.md task
    |
    v
Parse and validate TaskSpec
    |
    v
Create feature/task-id worktree from origin/main
    |
    v
Supervisor: Observe -> Reason -> Select one allowed action
    |
    +--> Explorer      (read-only repository context)
    +--> Implementer   (code and authorized tests)
    +--> Test Writer   (tests only)
    +--> Reviewer      (read-only decision and findings)
    |
    v
Scope validation -> pytest -> fingerprint -> review
    |                                      |
    |                           CHANGES_REQUESTED
    |                                      |
    +<-- Implementer remediation <---------+
    |
    v
APPROVED exact current fingerprint
    |
    +-- without --deliver --> finish locally and retain worktree
    |
    +-- with --deliver ----> commit -> push -> create PR -> cleanup
```

Cycle 1 is the initial implementation attempt. A validation, test, or review
failure can route findings back to the Implementer. Cycles 2–5 are remediation
attempts; a sixth implementation attempt is refused and the run moves to
`needs_input`.

The five-cycle limit is not a time delay. A one-minute task exits as soon as it
reaches a terminal state. The configured timeout is only an upper bound for an
individual agent invocation.

## State and `TODO.md` lifecycle

Internal workflow transitions are projected into the selected `TODO.md` task:

```text
ready/RECEIVED
  -> IMPLEMENTING
  -> TESTING
  -> REVIEWING
  -> APPROVED
  -> CREATING_PR
  -> PR creation complete
```

- A successful run without `--deliver` stops locally at `APPROVED`.
- `CREATING_PR` is written only when delivery is explicitly authorized.
- `PR creation complete` is written only after the PR URL is returned.
- `NEEDS_INPUT` means the agent needs human clarification or exhausted its
  bounded remediation budget.
- `FAILED` means execution or a deterministic gate failed.

## Worktrees and generated code

By default, task files are physically created in an external Git worktree:

```text
../CodedWorkspace/<repository-name>/<task-id>/
```

For this checkout, TASK-113 would use:

```text
/Users/tapasdas/work/workingFolder/CodedWorkspace/MyCodingAgent/task-113/
```

Within that worktree, generated code and tests use the paths declared by the
task, for example:

```text
workspace/greeting_service/Coding/
workspace/greeting_service/test/
```

Worktree behavior:

- Successful `--deliver`: remove the registered worktree after PR creation.
- Successful local run: retain the worktree so local changes are not lost.
- `needs_input` or `failed`: retain it for investigation and remediation.
- Unexpected remaining files: refuse cleanup and log `worktree.retained`.

Use `--no-worktree` only for control-plane development. It operates in the
current checkout and is not recommended for normal task execution.

## Logs, traces, and execution memory

Each run writes correlated, redacted records to:

```text
logs/<TASK-ID>.logs                         append-only trace across runs
.mycodeagent/runs/<run-id>/events.jsonl     machine-readable run events
.mycodeagent/runs/<run-id>/memory.json      centralized execution memory
.mycodeagent/tasks/<TASK-ID>/latest.json    pointer to the latest run
```

Useful commands:

```bash
tail -f logs/TASK-113.logs
python -m json.tool .mycodeagent/tasks/TASK-113/latest.json
python -m json.tool .mycodeagent/runs/<run-id>/memory.json
```

Events use the `mycodeagent.event.v1` schema and include UTC timestamp, run ID,
task ID, trace ID, event type, stage, status, cycle, and redacted details. Trace
files and stored artifacts are created with owner-only permissions.

## Commands

| Command | Purpose |
|---|---|
| `mycodeagent show-task TASK-ID` | Print the normalized task without running it. |
| `mycodeagent run TASK-ID` | Implement, test, and review one task locally. |
| `mycodeagent run TASK-ID --deliver` | Run one task through PR creation. |
| `mycodeagent submit` | Run the first ready/received task locally. |
| `mycodeagent submit --deliver` | Deliver the first ready/received task. |
| `mycodeagent status TASK-ID` | Print the latest persisted run reference. |
| `mycodeagent verify TASK-ID --worktree PATH` | Run deterministic validation against an existing worktree. |

Use an alternate task file or runtime configuration when needed:

```bash
mycodeagent --config /path/to/runtime.toml run TASK-113 --todo /path/to/TODO.md --deliver
```

Global options such as `--config` must appear before the subcommand.

## Runtime configuration and timeouts

`workflow_runtime.toml` controls the provider defaults and per-role overrides:

```toml
[workflow]
max_cycles = 5

[defaults]
harness = "codex"
model = "gpt-5.4-mini"
effort = "high"
time_limit_seconds = 1200

[paths]
# Relative to the primary repository root.
worktree_root = "../CodedWorkspace"

[agents.explorer]
read_only = true

[agents.implementer]
write_scope = "coding_and_authorized_tests"

[agents.test_writer]
write_scope = "tests"

[agents.reviewer]
read_only = true
```

`time_limit_seconds = 1200` is the maximum duration of one Supervisor or
sub-agent invocation; it does not make every invocation run for twenty minutes.
Role-specific limits can be set with `timeout_seconds` inside a role section.
The deterministic pytest runner has a separate 300-second upper bound. A
recognized transient Omnigent transport failure is retried once.

The maximum strategic implementation/remediation cycle count is fixed at five.
Configuration with another value is rejected.

### Worktree location and Windows paths

`paths.worktree_root` controls where task worktrees are created. A relative
value is resolved from the primary repository root. The default
`../CodedWorkspace` therefore keeps worktrees outside the primary checkout.
The final layout is:

```text
<worktree_root>/<repository-name>/<task-id>
```

For a fixed native Windows location, forward slashes are the simplest TOML
syntax:

```toml
[paths]
worktree_root = "C:/MyCodingAgent/worktrees"
```

Backslashes are also accepted, but use a TOML literal string or escape every
backslash:

```toml
[paths]
worktree_root = 'C:\MyCodingAgent\worktrees'
# Equivalent: "C:\\MyCodingAgent\\worktrees"
```

Environment variables in the value are expanded, so Windows installations may
also use:

```toml
[paths]
worktree_root = "%LOCALAPPDATA%/MyCodingAgent/worktrees"
```

When checking registered worktrees, MyCodeAgent parses Git's porcelain output
and compares normalized native paths. Consequently, `C:/Projects/worktree` and
`C:\Projects\worktree` are treated as the same Windows path. Git branch names
remain slash-separated identifiers such as `feature/task-113`; do not convert
branch-name slashes to backslashes.

## Implementation map

| Path | Responsibility |
|---|---|
| `src/mycodeagent/cli.py` | Command parsing, task selection, and result output. |
| `src/mycodeagent/task_parser.py` | `TODO.md` parsing and TaskSpec validation. |
| `src/mycodeagent/orchestrator.py` | Supervisor loop, routing, gates, and feedback. |
| `src/mycodeagent/agent_executor.py` | Omnigent invocation, timeout, retry, and output parsing. |
| `src/mycodeagent/state_store.py` | Legal transitions, atomic memory, and TODO status updates. |
| `src/mycodeagent/workspace.py` | External Git worktree creation and guarded cleanup. |
| `src/mycodeagent/validator.py` | Scope, required-file, secret, symlink, artifact, and fingerprint checks. |
| `src/mycodeagent/test_runner.py` | Authoritative task-level pytest execution. |
| `src/mycodeagent/delivery.py` | Repository check, commit, push, and `gh pr create`. |
| `src/mycodeagent/observability.py` | JSONL logging, correlation, permissions, and redaction. |
| `agents/*.yaml` | Supervisor and specialized role prompt contracts. |
| `workflow_runtime.toml` | Harness, model, effort, timeout, and role configuration. |

Omnigent is the LLM execution harness. It runs each supplied agent definition;
it does not own MyCodeAgent's workflow state or decide which role runs next.
The Python orchestrator asks the Supervisor for one allowlisted action, derives
the corresponding role, executes deterministic gates, persists the result, and
then starts the next strategic step.

## Troubleshooting

### The run ends at `APPROVED` and no PR exists

The command did not include delivery authorization. Run a ready task with:

```bash
mycodeagent run TASK-ID --deliver
```

Do not rerun an already-approved task blindly. Inspect `TODO.md`, the stored
state, branch, and retained worktree first.

### The run ends at `needs_input`

Inspect the latest memory and task trace:

```bash
mycodeagent status TASK-ID
tail -n 100 logs/TASK-ID.logs
```

Resolve missing requirements or the recorded validation/test/review findings.
The worktree is retained.

### The run ends at `failed`

Look for the last error event in `logs/TASK-ID.logs` and the run-specific
`events.jsonl`. Common causes include provider authentication, an unavailable
Omnigent executable, timeout, missing `origin/main`, repository mismatch,
failed push, or failed `gh pr create`.

CLI exit codes are:

- `0`: local completion or successful delivery.
- `1`: workflow ended before completion, such as `needs_input` or `failed`.
- `2`: configuration, parsing, validation, filesystem, or command error.

### The worktree directory still exists after delivery

Cleanup is intentionally conservative. Check:

```bash
git worktree list
git -C /path/to/worktree status --short --untracked-files=all
```

MyCodeAgent retains the worktree when unexpected residue could be lost. Remove
or preserve those files deliberately before performing manual Git cleanup.

On Windows PowerShell, quote paths containing spaces:

```powershell
git worktree list
git -C "C:\My Worktrees\MyCodingAgent\task-113" status --short --untracked-files=all
```

If Git displays a worktree with forward slashes while PowerShell displays
backslashes, that difference alone is harmless. If registration still fails,
confirm that both paths resolve to the same drive and directory and that the
configured `paths.worktree_root` points to the intended location.

### `mycodeagent: 'main' is not a valid AgentRole`

The current implementation does not interpret Omnigent's provider session name
`main` as a MyCodeAgent role. Ensure the editable installation points to this
checkout:

```bash
python -m pip install -e .
command -v mycodeagent
```

## Current enforcement boundary

The control plane deterministically validates task paths, changed files,
required artifacts, tests, fingerprints, state transitions, and delivery. The
role prompts also declare read-only and write-scope responsibilities. Those
role-level filesystem restrictions are currently prompt/config contracts, not
a complete OS-level sandbox boundary. Run MyCodeAgent only in repositories and
with credentials appropriate for the selected LLM harness, and review every
generated pull request before merging.
