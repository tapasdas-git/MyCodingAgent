"""Command-line entry point for the hierarchical MyCodeAgent runtime."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .agent_executor import OmnigentAgentExecutor
from .config import load_workflow_config
from .errors import MyCodeAgentError
from .orchestrator import SupervisorOrchestrator
from .task_parser import select_task
from .validator import WorkspaceValidator

ROOT = Path(__file__).resolve().parents[2]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mycodeagent", description="Hierarchical MyCodeAgent supervisor")
    parser.add_argument("--config", type=Path, default=ROOT / "workflow_runtime.toml")
    commands = parser.add_subparsers(dest="command", required=True)
    for name, help_text in (("submit", "Run the first ready task"), ("run", "Run a specific task")):
        command = commands.add_parser(name, help=help_text)
        command.add_argument("task_id", nargs="?" if name == "submit" else None)
        command.add_argument("--todo", type=Path, default=ROOT / "TODO.md")
        command.add_argument("--no-worktree", action="store_true", help="Operate in the current tree (development only)")
        command.add_argument("--deliver", action="store_true", help="Authorize delivery after exact-fingerprint approval")
    show = commands.add_parser("show-task", help="Print the normalized TaskSpec")
    show.add_argument("task_id", nargs="?")
    show.add_argument("--todo", type=Path, default=ROOT / "TODO.md")
    status = commands.add_parser("status", help="Show the latest persisted state for a task")
    status.add_argument("task_id")
    verify = commands.add_parser("verify", help="Run deterministic workspace validation")
    verify.add_argument("task_id")
    verify.add_argument("--todo", type=Path, default=ROOT / "TODO.md")
    verify.add_argument("--worktree", type=Path, default=ROOT)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "show-task":
            print(json.dumps(select_task(args.todo, args.task_id).to_dict(), indent=2))
            return 0
        if args.command == "status":
            path = ROOT / ".mycodeagent" / "tasks" / args.task_id.upper() / "latest.json"
            if not path.exists():
                print(f"No execution state for {args.task_id.upper()}", file=sys.stderr)
                return 1
            print(path.read_text(encoding="utf-8"), end="")
            return 0
        if args.command == "verify":
            result = WorkspaceValidator(args.worktree, select_task(args.todo, args.task_id)).validate()
            print(json.dumps({"passed": result.passed, "errors": result.errors,
                              "changed_files": result.changed_files,
                              "fingerprint": result.fingerprint}, indent=2))
            return 0 if result.passed else 1

        task = select_task(args.todo, args.task_id)
        config = load_workflow_config(args.config)
        executor = OmnigentAgentExecutor(ROOT, config, ROOT / "agents")
        supervisor = SupervisorOrchestrator(ROOT, config, executor, create_worktree=not args.no_worktree)
        print(f"Starting {task.task_id} — {task.title}")
        memory = supervisor.run(task, deliver=args.deliver)
        print(json.dumps({"run_id": memory.run_id, "state": memory.state.value,
                          "cycles": memory.cycle, "worktree": memory.worktree}, indent=2))
        return 0 if memory.state.value in {"completed", "delivered"} else 1
    except (MyCodeAgentError, OSError, ValueError) as exc:
        print(f"mycodeagent: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
