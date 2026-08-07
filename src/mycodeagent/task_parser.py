"""Parse complete task specifications from TODO.md."""

from __future__ import annotations

import re
from pathlib import Path, PurePosixPath

from .errors import TaskNotFoundError, TaskParseError
from .models import TaskIntent, TaskSource, TaskSpec, WorkspaceBoundary

HEADING = re.compile(
    r"^##\s+(?P<id>[A-Z0-9]+-\d+)\s*\|\s*(?P<state>[^|]+?)\s*\|\s*"
    r"(?P<priority>[^|]+?)\s*\|\s*(?P<title>.+?)\s*$",
    re.MULTILINE,
)
FIELD = re.compile(r"^-\s+(?P<name>[^:]+):\s*(?P<value>.*)$")
BACKTICK_PATH = re.compile(r"`([^`]+)`")
READY_STATES = {"ready", "received"}


def _intent(title: str, section: str) -> TaskIntent:
    value = f"{title} {section[:500]}".lower()
    if "[bug" in value or "bug fix" in value or " fix " in f" {value} ":
        return TaskIntent.BUG_FIX
    if "[feature" in value or "implement" in value or "build" in value or "add " in value:
        return TaskIntent.FEATURE
    if "refactor" in value:
        return TaskIntent.REFACTOR
    if "review" in value:
        return TaskIntent.REVIEW
    if "test" in value:
        return TaskIntent.TEST
    if "document" in value or "docs" in value:
        return TaskIntent.DOCUMENTATION
    if "investigat" in value or "research" in value:
        return TaskIntent.INVESTIGATION
    return TaskIntent.UNKNOWN


def _safe_workspace_path(value: str, field_name: str) -> str:
    normalized = value.strip().rstrip("/")
    path = PurePosixPath(normalized)
    if path.is_absolute() or ".." in path.parts:
        raise TaskParseError(f"Unsafe {field_name} path: {value}")
    if not path.parts or path.parts[0] != "workspace":
        raise TaskParseError(f"{field_name} must be inside workspace/: {value}")
    return path.as_posix()


def _section_items(lines: list[str], heading: str) -> list[str]:
    start = None
    target = heading.lower()
    result: list[str] = []
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.lower().startswith((f"- {target}:", f"{target}:")):
            start = index + 1
            inline = stripped.split(":", 1)[1].strip()
            if inline:
                result.append(inline)
            continue
        if start is not None:
            if line.startswith("- ") and not line.startswith("  "):
                break
            item = stripped
            if item.startswith("-"):
                item = item[1:].strip()
            if item:
                result.append(item)
    return result


def _top_level_value(lines: list[str], name: str) -> str:
    target = name.lower()
    for line in lines:
        match = FIELD.match(line.strip())
        if match and match.group("name").strip().lower() == target:
            return match.group("value").strip()
    return ""


def _workspace(lines: list[str], title: str, task_id: str) -> WorkspaceBoundary:
    source = tests = requirements = ""
    in_boundary = False
    for line in lines:
        stripped = line.strip()
        if stripped.lower().startswith("- workspace boundary:"):
            in_boundary = True
            continue
        if in_boundary and line.startswith("- ") and not line.startswith("  "):
            break
        if not in_boundary:
            continue
        match = FIELD.match(stripped)
        if not match:
            continue
        name = match.group("name").strip().lower()
        value_match = BACKTICK_PATH.search(match.group("value"))
        value = value_match.group(1) if value_match else match.group("value").strip()
        if name == "source":
            source = value
        elif name == "tests":
            tests = value
        elif name == "requirements":
            requirements = value

    if not source or not tests:
        title_path = next(
            (item for item in BACKTICK_PATH.findall(title) if item.startswith("workspace/")),
            "",
        )
        if not title_path:
            title_path = next(
                (
                    item.split("/Coding/", 1)[0].split("/test/", 1)[0]
                    for line in lines
                    for item in BACKTICK_PATH.findall(line)
                    if item.startswith("workspace/")
                ),
                "",
            )
        if title_path:
            root = title_path.rstrip("/")
            source = source or f"{root}/Coding"
            tests = tests or f"{root}/test"

    if not source or not tests:
        # Legacy/completed tasks may predate explicit workspace boundaries. A
        # deterministic fallback keeps them inspectable; ready tasks should
        # still declare explicit boundaries in their acceptance contract.
        root = f"workspace/{task_id.lower().replace('-', '_')}"
        source = f"{root}/Coding"
        tests = f"{root}/test"

    source = _safe_workspace_path(source, "source")
    tests = _safe_workspace_path(tests, "tests")
    source_root = PurePosixPath(source)
    test_root = PurePosixPath(tests)
    common = []
    for left, right in zip(source_root.parts, test_root.parts):
        if left != right:
            break
        common.append(left)
    if len(common) < 2:
        raise TaskParseError("Source and test paths must share a task workspace root")
    root = PurePosixPath(*common).as_posix()
    requirements_value = _safe_workspace_path(requirements, "requirements") if requirements else None
    if requirements_value and not _is_within(requirements_value, root):
        raise TaskParseError(
            f"Requirements path must be inside task workspace root '{root}': "
            f"{requirements_value}"
        )
    return WorkspaceBoundary(
        root=root,
        coding_dir=source,
        test_dir=tests,
        requirements_file=requirements_value,
    )


def _is_within(candidate: str, root: str) -> bool:
    path = PurePosixPath(candidate)
    boundary = PurePosixPath(root)
    return path == boundary or boundary in path.parents


def _required_files(lines: list[str], workspace: WorkspaceBoundary) -> tuple[str, ...]:
    candidates: list[str] = []
    for line in lines:
        for value in BACKTICK_PATH.findall(line):
            if "/" not in value and not value.endswith((".py", ".txt", ".toml", ".yaml", ".yml")):
                continue
            if value.startswith("workspace/") and PurePosixPath(value.rstrip("/")).suffix:
                candidate = value.rstrip("/")
            elif value.endswith((".py", ".txt", ".toml", ".yaml", ".yml")):
                if "test" in value.lower():
                    candidate = f"{workspace.test_dir}/{PurePosixPath(value).name}"
                else:
                    candidate = f"{workspace.coding_dir}/{PurePosixPath(value).name}"
            else:
                continue
            if not _is_within(candidate, workspace.root):
                raise TaskParseError(
                    f"Required file must be inside task workspace root "
                    f"'{workspace.root}': {candidate}"
                )
            if candidate not in candidates:
                candidates.append(candidate)
    if workspace.requirements_file and workspace.requirements_file not in candidates:
        candidates.append(workspace.requirements_file)
    return tuple(candidates)


def parse_tasks(todo_path: Path) -> list[TaskSpec]:
    if not todo_path.exists():
        raise TaskParseError(f"Task source does not exist: {todo_path}")
    content = todo_path.read_text(encoding="utf-8")
    matches = list(HEADING.finditer(content))
    tasks: list[TaskSpec] = []
    seen: set[str] = set()
    for index, match in enumerate(matches):
        task_id = match.group("id").upper()
        if task_id in seen:
            raise TaskParseError(f"Duplicate task ID: {task_id}")
        seen.add(task_id)
        end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
        section = content[match.start():end].strip()
        lines = section.splitlines()[1:]
        title = match.group("title").strip()
        dependencies_value = _top_level_value(lines, "Depends on")
        dependencies = () if dependencies_value.lower() in ("", "none") else tuple(
            value.strip() for value in dependencies_value.split(",") if value.strip()
        )
        acceptance = tuple(_section_items(lines, "Acceptance"))
        if not acceptance:
            raise TaskParseError(f"{task_id} has no Acceptance criteria")
        workspace = _workspace(lines, title, task_id)
        architecture = tuple(_section_items(lines, "Architecture & Tech Stack"))
        security = tuple(_section_items(lines, "API Key & Secrets Management"))
        tasks.append(
            TaskSpec(
                task_id=task_id,
                source=TaskSource.TODO,
                source_reference=str(todo_path),
                state=match.group("state").strip().lower(),
                priority=match.group("priority").strip(),
                title=title,
                intent=_intent(title, section),
                outcome=_top_level_value(lines, "Outcome"),
                repository=_top_level_value(lines, "Repository") or None,
                dependencies=dependencies,
                architecture_requirements=architecture,
                security_requirements=security,
                acceptance_criteria=acceptance,
                required_files=_required_files(lines, workspace),
                workspace=workspace,
                raw_section=section,
            )
        )
    return tasks


def select_task(todo_path: Path, task_id: str | None = None) -> TaskSpec:
    tasks = parse_tasks(todo_path)
    if task_id:
        normalized = task_id.upper()
        for task in tasks:
            if task.task_id == normalized:
                return task
        raise TaskNotFoundError(f"Task ID '{normalized}' not found in {todo_path.name}")
    for task in tasks:
        if task.state.lower() in READY_STATES:
            return task
    raise TaskNotFoundError("No task with state 'ready' found")


# Compatibility for callers of the original launcher.
def parse_todo_file(todo_path: Path) -> dict[str, dict[str, str]]:
    return {
        task.task_id: {
            "state": task.state,
            "priority": task.priority,
            "title": task.title,
        }
        for task in parse_tasks(todo_path)
    }


def get_first_ready_task(tasks: dict[str, dict[str, str]]) -> str | None:
    return next((task_id for task_id, info in tasks.items() if info["state"] == "ready"), None)
