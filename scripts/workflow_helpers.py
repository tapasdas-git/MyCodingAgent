"""Workflow Helpers: Handles deterministic tasks (Changelog & PR Creation) to save LLM tokens."""

import argparse
import re
import subprocess
import sys
from pathlib import Path


def get_default_branch() -> str:
    """Safely detect whether 'main' or 'master' is the primary remote branch."""
    for branch in ["main", "master"]:
        res = subprocess.run(
            ["git", "rev-parse", "--verify", f"refs/remotes/origin/{branch}"],
            capture_output=True,
            text=True,
        )
        if res.returncode == 0:
            return branch
    return "main"


def update_changelog(task_id: str, todo_path: str = "TODO.md", changelog_path: str = "CHANGELOG.md") -> None:
    """Extracts task summary from TODO.md and appends it to CHANGELOG.md."""
    print(f"🔍 Reading {todo_path} for task {task_id}...", flush=True)
    todo_file = Path(todo_path)
    changelog_file = Path(changelog_path)

    if not todo_file.exists():
        print(f"❌ Error: {todo_path} does not exist.", file=sys.stderr, flush=True)
        sys.exit(1)

    task_title = None
    for line in todo_file.read_text().splitlines():
        if task_id in line:
            match = re.search(rf"{task_id}\s*\|\s* ready\s*\|\s*\w+\s*\|\s*(.*)", line)
            if match:
                task_title = match.group(1).strip()
                break
            task_title = line.strip()

    if not task_title:
        task_title = f"Completed task {task_id}"

    changelog_content = changelog_file.read_text() if changelog_file.exists() else "# Changelog\n\n## Unreleased\n"
    new_entry = f"- **{task_id}**: {task_title}"

    if "## Unreleased" in changelog_content:
        changelog_content = changelog_content.replace("## Unreleased\n", f"## Unreleased\n{new_entry}\n")
    else:
        changelog_content = f"## Unreleased\n{new_entry}\n\n" + changelog_content

    changelog_file.write_text(changelog_content)
    print(f"✅ Updated {changelog_path} with: {new_entry}", flush=True)


def create_pull_request(task_id: str, task_dir: str) -> None:
    """Stages specific task directory, commits, pushes branch, and creates PR."""
    print(f"🚀 Initializing PR process for Task ID: {task_id} in directory: {task_dir}...", flush=True)
    branch_name = f"feature/{task_id.lower()}"

    def run_cmd(cmd: list[str], allow_fail: bool = False) -> str:
        print(f"⚙️ Running command: {' '.join(cmd)}", flush=True)
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0 and not allow_fail:
            print(f"❌ Error running {' '.join(cmd)}:\n{res.stderr}", file=sys.stderr, flush=True)
            sys.exit(1)
        return res.stdout.strip()

    # Safely resolve target base branch ('main' or 'master')
    base_branch = get_default_branch()
    print(f"🎯 Target base branch resolved to: {base_branch}", flush=True)

    run_cmd(["git", "checkout", "-B", branch_name])
    run_cmd(["git", "add", f"{task_dir}/Coding/", f"{task_dir}/test/", "CHANGELOG.md"])

    # Check if there are staged changes ready to commit
    res = subprocess.run(["git", "diff", "--cached", "--quiet"])
    if res.returncode != 0:
        # Returncode != 0 means there ARE staged changes to commit
        run_cmd(["git", "commit", "-m", f"feat({task_id}): implement task solution and tests"])
    else:
        print("ℹ️ No new staged changes to commit; proceeding to push.", flush=True)

    run_cmd(["git", "push", "-u", "origin", branch_name])

    print("🐙 Creating Pull Request on GitHub...", flush=True)
    pr_url = run_cmd([
        "gh", "pr", "create",
        "--base", base_branch,
        "--head", branch_name,
        "--title", f"feat({task_id}): automated implementation",
        "--body", f"Automated PR generated for task `{task_id}` inside isolated directory `{task_dir}/`."
    ])

    print(f"\n✅ Pull Request Created Successfully!\n🔗 {pr_url}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Workflow Helper Utility")
    parser.add_argument("action", choices=["changelog", "pr"], help="Action to execute")
    parser.add_argument("--task-id", required=True, help="Task identifier (e.g., SWAF-045)")
    parser.add_argument("--task-dir", default="", help="Task directory path (e.g., fibonacci)")

    args = parser.parse_args()

    if args.action == "changelog":
        update_changelog(args.task_id)
    elif args.action == "pr":
        if not args.task_dir:
            print("❌ Error: --task-dir is required when action is 'pr'.", file=sys.stderr, flush=True)
            sys.exit(1)
        create_pull_request(args.task_id, args.task_dir)