#!/usr/bin/env python3
"""Run the Omnigent workflow using model settings and tasks from TODO.md."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SETTINGS_PATH = ROOT / "workflow_runtime.toml"
WORKFLOW_PATH = ROOT / "coding_agent.yaml"

# Regex matching: ## <ID> | <state> | <priority> | <title>
TASK_HEADING = re.compile(
    r"^##\s+([A-Z0-9]+-\d+)\s*\|\s*(\w+)\s*\|\s*(P[0-3])\s*\|\s*(.+?)\s*$",
    re.MULTILINE
)
# Reads TODO.md, locates the header matching task_id, and extracts task specs.
def parse_todo_file(todo_path: Path) -> dict[str, dict[str, str]]:
    """Parse TODO.md and return structured task dictionary."""
    if not todo_path.exists():
        print(f"Error: Could not find {todo_path}", file=sys.stderr)
        sys.exit(1)

    content = todo_path.read_text(encoding="utf-8")
    tasks = {}
    for match in TASK_HEADING.finditer(content):
        task_id, state, priority, title = match.groups()
        tasks[task_id] = {
            "state": state.lower(),
            "priority": priority,
            "title": title
        }
    return tasks

def get_first_ready_task(tasks: dict[str, dict[str, str]]) -> str | None:
    """Find the first task marked with state 'ready'."""
    for task_id, info in tasks.items():
        if info["state"] == "ready":
            return task_id
    return None
# Invokes the Omnigent engine runner for a specific stage in the workflow YAML
def execute_omnigent_stage(prompt: str, target_stage: str | None = None) -> int:
    """Loads runtime settings and executes the workflow or targeted sub-tool stage."""
    with SETTINGS_PATH.open("rb") as settings_file:
        settings = tomllib.load(settings_file)

    required = ("harness", "model", "effort", "time_limit_seconds")
    missing = [key for key in required if not settings.get(key)]
    if missing:
        raise SystemExit(f"Missing required runtime setting(s): {', '.join(missing)}")

    environment = os.environ.copy()
    environment["OMNIGENT_WORKFLOW_MODEL"] = str(settings["model"])
    environment["OMNIGENT_WORKFLOW_EFFORT"] = str(settings["effort"])

    workflow_source = WORKFLOW_PATH.read_text(encoding="utf-8")
    rendered_workflow = (
        workflow_source.replace("${OMNIGENT_WORKFLOW_MODEL}", str(settings["model"]))
        .replace("${OMNIGENT_WORKFLOW_EFFORT}", str(settings["effort"]))
    )

    with tempfile.TemporaryDirectory(prefix="omnigent-workflow-") as temp_dir:
        rendered_path = Path(temp_dir) / WORKFLOW_PATH.name
        rendered_path.write_text(rendered_workflow, encoding="utf-8")

        if target_stage:
            prompt = (
                f"STAGE ONLY: {target_stage}\n"
                "Invoke only the named workflow stage. Do not invoke, delegate to, "
                "or perform any other stage.\n\n"
                f"{prompt}"
            )

        command = [
            "omnigent",
            "run",
            str(rendered_path),
            "--harness",
            str(settings["harness"]),
            "--model",
            str(settings["model"]),
            "-p",
            prompt,
        ]
        try:
            completed = subprocess.run(
                command,
                cwd=ROOT,
                env=environment,
                timeout=int(settings["time_limit_seconds"]),
                check=False,
            )
            return completed.returncode
        except subprocess.TimeoutExpired:
            print(f"Workflow exceeded timeout limit.", file=sys.stderr)
            return 124
# """Parses CLI flags (run, verify, review, deliver, submit) and routes execution."""
def main() -> int:
    parser = argparse.ArgumentParser(prog="mycodeagent", description="MyCodeAgent Workflow CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # 1. 'submit' command
    submit_parser = subparsers.add_parser("submit", help="Run the pipeline on the first ready task")
    submit_parser.add_argument("--todo", type=Path, default=ROOT / "TODO.md", help="Path to TODO.md file")

    # 2. Individual stage commands for troubleshooting
    for stage_cmd in ["run", "verify", "review", "deliver"]:
        stage_parser = subparsers.add_parser(stage_cmd, help=f"Troubleshoot the '{stage_cmd}' stage individually")
        stage_parser.add_argument("task_id", help="Task ID (e.g., SWAF-042)")
        stage_parser.add_argument("--todo", type=Path, default=ROOT / "TODO.md", help="Path to TODO.md file")

    args = parser.parse_args()

    # Default action if no subcommand is passed
    if not args.command:
        parser.print_help()
        return 1

    tasks = parse_todo_file(args.todo)

    # Handle 'submit' command
    if args.command == "submit":
        task_id = get_first_ready_task(tasks)
        if not task_id:
            print("No task with state 'ready' found in TODO.md.", file=sys.stderr)
            return 1
        
        print(f"Submitting first ready task: {task_id} — {tasks[task_id]['title']}")
        prompt = (
            f"Execute task {task_id}: {tasks[task_id]['title']}.\n"
            f"Context & Requirements:\n"
            f"- Read the section for {task_id} inside TODO.md.\n"
            f"- STRICT GROUNDING: Do not hallucinate imports, methods, or third-party packages not listed in project configuration.\n"
            f"- VERIFICATION: Write accompanying unit tests that validate every Acceptance criterion. Run test suite locally to verify 100% pass rate before requesting review."
)
        return execute_omnigent_stage(prompt)

    # Handle individual troubleshooting stages
    stage_map = {
        "run": "implement_task",
        "verify": "implement_task", # Or targeted testing agent
        "review": "review_change",
        "deliver": "create_pull_request"
    }

    target_task = args.task_id.upper()
    if target_task not in tasks:
        print(f"Task ID '{target_task}' not found in {args.todo.name}.", file=sys.stderr)
        return 1

    stage_tool = stage_map[args.command]
    print(f"Running individual stage '{args.command}' ({stage_tool}) for {target_task}...")
    prompt = f"Target stage troubleshooting for {target_task} using {stage_tool}."
    return execute_omnigent_stage(prompt, target_stage=stage_tool)


if __name__ == "__main__":
    raise SystemExit(main())
