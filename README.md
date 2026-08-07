# MyCodeAgent

MyCodeAgent is a hierarchical software-development agent. Omnigent is the
meta-harness, a Supervisor LLM performs one bounded ReAct decision at a time,
and specialized Explorer, Implementer, Test Writer, and Reviewer LLM agents do
the delegated work. Deterministic Python code owns state transitions, workspace
isolation, tests, fingerprints, the five-cycle limit, logging, and PR gates.

## Execution flow

```text
TODO.md -> normalize TaskSpec -> create Git worktree
                  |
                  v
       Supervisor Observe / Reason / Select
                  |
       +----------+-----------+----------+
       v          v           v          v
    Explorer  Implementer  Test Writer  Reviewer
                  ^                      |
                  |  ReviewContext       |
                  +-- CHANGES_REQUESTED--+
                  |
       validate -> pytest -> fingerprint -> re-review
                  |
          APPROVED exact fingerprint
                  v
          commit -> push -> create PR
```

Cycle 1 is the initial implementation, test, and review. Review or test failures
are persisted in centralized execution memory and routed back to the
Implementer. Cycles 2–5 repeat remediation, deterministic validation/testing,
and final review. No sixth automatic cycle is allowed.

`TODO.md` exposes business-facing lifecycle labels: `RECEIVED`, `IMPLEMENTING`,
`TESTING`, `REVIEWING`, `APPROVED`, `CREATING_PR`, and
`PR creation complete`. Local-only runs remain `APPROVED`; `CREATING_PR` is
written only after explicit `--deliver` authorization.

The Supervisor returns only an action and rationale. MyCodeAgent maps that
action to a specialized role deterministically; provider session identities
such as Omnigent's `main` role are never interpreted as agent roles.

Loop ownership is hierarchical. The Supervisor owns the bounded strategic
Observe–Reason–Select loop and all workflow transitions. Each specialized agent
may use only a bounded tactical inspect/edit/check loop within one delegated
action; it cannot invoke another agent, select a workflow stage, approve its own
work, or deliver changes. Deterministic Python owns timeouts, one transient
transport retry, validation, tests, fingerprints, cycle limits, and delivery.

## Provider configuration

Agent providers are selected in `workflow_runtime.toml`; implementation code is
provider-neutral. Codex is the current default. Omnigent/LiteLLM can route a
role to Claude or Gemini by changing only that role's harness/model settings:

```toml
[agents.implementer]
harness = "anthropic"
model = "claude-model-name"
write_scope = "coding_and_authorized_tests"
```

## Layout

```text
agents/                     Omnigent role definitions
src/mycodeagent/cli.py      CLI routing
src/mycodeagent/task_parser.py  TODO.md -> TaskSpec
src/mycodeagent/orchestrator.py Supervisor ReAct feedback loop
src/mycodeagent/state_store.py  Atomic memory and state machine
src/mycodeagent/agent_executor.py Omnigent role invocation
src/mycodeagent/workspace.py     Git worktree isolation
src/mycodeagent/validator.py     Scope, artifact, secret, fingerprint gates
src/mycodeagent/test_runner.py   Deterministic pytest execution
src/mycodeagent/delivery.py      Exact-approval commit/push/PR gate
src/mycodeagent/observability.py JSONL events, traces, and redaction
```

## Install and use

Requires Python 3.11+, Git, Omnigent, pytest, and the GitHub CLI for delivery.
When multiple Omnigent versions are installed, set
`MYCODEAGENT_OMNIGENT_EXECUTABLE` to the binary compatible with the configured
Omnigent database.

```bash
python3 -m venv venv
source venv/bin/activate
pip install -e .

mycodeagent show-task TASK-107
mycodeagent submit
mycodeagent run TASK-107
mycodeagent status TASK-107
mycodeagent verify TASK-107 --worktree /path/to/task/worktree
```

`submit` selects the first `ready` TODO task. `run` selects a specific task.
Both create an isolated worktree by default. Add `--deliver` to explicitly
authorize commit, push, and PR creation after final approval. Without it, an
approved run finishes locally and makes no remote changes.

Task worktrees are kept outside the primary checkout under
`../CodedWorkspace/<repository>/<task-id>/`. Repository namespacing
prevents identical task IDs in sibling repositories from colliding.
After commit, push, and pull-request creation succeed, the registered task
worktree is removed automatically. Local-only `completed` worktrees are kept
because their uncommitted implementation would otherwise be lost. Cleanup is
also skipped when unexpected residual files are detected.

## Task contract

Each TODO task must define acceptance criteria and a workspace boundary. Source
belongs under `workspace/<task>/Coding/`; tests belong under
`workspace/<task>/test/`. Required files are derived from the task, and changes
outside those paths fail deterministic validation.

Run the control-plane test suite with:

```bash
python -m pytest -q -p no:cacheprovider
```

## Logs and traces

Every workflow event is written to both a run-specific JSONL trace and an
append-only task trace:

```text
.mycodeagent/runs/<run-id>/events.jsonl
logs/<task-id>.logs
```

Records use the `mycodeagent.event.v1` schema and include UTC timestamp,
run/task/trace correlation IDs, event type, stage, status, cycle, and recursively
redacted details. Trace files and stored artifacts use owner-only `0600`
permissions. Follow a task across runs with `tail -f logs/TASK-108.logs`.
