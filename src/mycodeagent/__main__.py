"""Compatibility launcher for ``python -m mycodeagent``."""

from .cli import main
from .task_parser import get_first_ready_task, parse_todo_file

__all__ = ["get_first_ready_task", "main", "parse_todo_file"]

if __name__ == "__main__":
    raise SystemExit(main())
