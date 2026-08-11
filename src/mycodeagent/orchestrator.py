"""Bounded ReAct orchestration using an LLM Supervisor and deterministic gates."""

from __future__ import annotations

import subprocess
import sys
import uuid
from dataclasses import asdict
from pathlib import Path

from .agent_executor import OmnigentAgentExecutor
from .config import WorkflowConfig
from .delivery import PullRequestDelivery
from .errors import AgentExecutionError, IterationLimitError, ValidationError
from .models import (
    AgentResult,
    AgentRole,
    ExecutionMemory,
    ReviewDecision,
    SupervisorAction,
    TaskSpec,
    WorkflowState,
)
from .observability import EventLogger, TraceContext, redact
from .state_store import StateStore
from .test_runner import TestRunner
from .validator import WorkspaceValidator
from .workspace import WorktreeManager


class SupervisorOrchestrator:
    """Coordinates the hierarchical workflow; the Supervisor LLM chooses each action."""

    def __init__(
        self,
        repository_root: Path,
        config: WorkflowConfig,
        executor: OmnigentAgentExecutor,
        *,
        python_executable: str = sys.executable,
        create_worktree: bool = True,
    ) -> None:
        self.root = repository_root.resolve()
        self.config = config
        self.executor = executor
        self.state = StateStore(self.root)
        worktree_root = config.worktree_root
        if not worktree_root.is_absolute():
            worktree_root = self.root / worktree_root
        self.worktrees = WorktreeManager(self.root, worktree_root=worktree_root)
        self.tests = TestRunner(python_executable)
        self.delivery = PullRequestDelivery()
        self.create_worktree = create_worktree

    def run(self, task: TaskSpec, *, deliver: bool = False, max_steps: int = 50) -> ExecutionMemory:
        run_id = f"{task.task_id.lower()}-{uuid.uuid4().hex[:12]}"
        memory = ExecutionMemory(run_id=run_id, task=task, max_cycles=self.config.max_cycles)
        trace = TraceContext.create(run_id, task.task_id)
        logger = EventLogger(self.root, trace)
        if self.create_worktree:
            context = self.worktrees.create(task)
            memory.worktree = str(context.path)
            memory.base_commit = context.base_commit
        else:
            memory.worktree = str(self.root)
        self.state.initialize(memory)
        self.state.transition(memory, WorkflowState.WORKING)
        logger.event("workflow.started", stage="supervisor", status="ok", details={"task": task.to_dict()})

        for _ in range(max_steps):
            if memory.state in (
                WorkflowState.COMPLETED,
                WorkflowState.DELIVERED,
                WorkflowState.FAILED,
                WorkflowState.NEEDS_INPUT,
            ):
                return memory
            available = self.available_actions(memory, deliver=deliver)
            try:
                decision = self.executor.supervisor_decision(memory, available)
                memory.decisions.append(
                    {"action": decision.action.value, "role": decision.role.value if decision.role else None, "rationale": decision.rationale}
                )
                logger.event(
                    "supervisor.decision",
                    stage="supervisor",
                    status="ok",
                    cycle=memory.cycle,
                    details=memory.decisions[-1],
                )
                self._execute(memory, decision.action, logger, deliver=deliver)
                self.state.save_memory(memory)
            except IterationLimitError:
                self.state.transition(memory, WorkflowState.NEEDS_INPUT)
            except (AgentExecutionError, ValidationError) as exc:
                memory.errors.append(
                    {
                        "stage": "supervisor",
                        "cycle": memory.cycle,
                        "message": redact(str(exc)),
                    }
                )
                logger.event(
                    "workflow.error",
                    stage="supervisor",
                    status="failed",
                    cycle=memory.cycle,
                    details={"error": str(exc)},
                )
                self._fail(memory)
                self.state.save_memory(memory)
        if memory.state not in (
            WorkflowState.COMPLETED,
            WorkflowState.DELIVERED,
            WorkflowState.NEEDS_INPUT,
            WorkflowState.FAILED,
        ):
            memory.errors.append({
                "stage": "supervisor",
                "cycle": memory.cycle,
                "message": f"Strategic loop exhausted its {max_steps}-step budget",
            })
            self._fail(memory)
            self.state.save_memory(memory)
        return memory

    @staticmethod
    def available_actions(memory: ExecutionMemory, *, deliver: bool) -> tuple[SupervisorAction, ...]:
        working_actions = (
            (SupervisorAction.IMPLEMENT, SupervisorAction.REQUEST_INPUT)
            if memory.repository_context
            else (SupervisorAction.EXPLORE, SupervisorAction.IMPLEMENT, SupervisorAction.REQUEST_INPUT)
        )
        mapping = {
            WorkflowState.WORKING: working_actions,
            WorkflowState.IMPLEMENTING: (SupervisorAction.WRITE_TESTS, SupervisorAction.VALIDATE),
            WorkflowState.VALIDATING: (SupervisorAction.VALIDATE,),
            WorkflowState.TESTING: (SupervisorAction.RUN_TESTS,),
            WorkflowState.REVIEWING: (SupervisorAction.REVIEW,),
            WorkflowState.CHANGES_REQUESTED: (SupervisorAction.REMEDIATE, SupervisorAction.REQUEST_INPUT),
            WorkflowState.APPROVED: (SupervisorAction.DELIVER,) if deliver else (SupervisorAction.FINISH,),
        }
        return mapping.get(memory.state, (SupervisorAction.FAIL,))

    def _execute(
        self,
        memory: ExecutionMemory,
        action: SupervisorAction,
        logger: EventLogger,
        *,
        deliver: bool,
    ) -> None:
        if action is SupervisorAction.EXPLORE:
            result = self._invoke_role(AgentRole.EXPLORER, memory, self._context(memory), logger)
            memory.agent_results.append(self._agent_record(result))
            memory.repository_context = {"summary": result.summary}
            return
        if action in (SupervisorAction.IMPLEMENT, SupervisorAction.REMEDIATE):
            self.state.start_cycle(memory)
            self.state.transition(memory, WorkflowState.IMPLEMENTING)
            request = self._context(memory)
            request["mode"] = "remediation" if action is SupervisorAction.REMEDIATE else "initial_implementation"
            request["review_context"] = memory.unresolved_findings
            result = self._invoke_role(AgentRole.IMPLEMENTER, memory, request, logger)
            memory.agent_results.append(self._agent_record(result))
            memory.current_fingerprint = ""
            return
        if action is SupervisorAction.WRITE_TESTS:
            result = self._invoke_role(AgentRole.TEST_WRITER, memory, self._context(memory), logger)
            memory.agent_results.append(self._agent_record(result))
            return
        if action is SupervisorAction.VALIDATE:
            if memory.state is WorkflowState.IMPLEMENTING:
                self.state.transition(memory, WorkflowState.VALIDATING)
            logger.event("validation.started", stage="validation", status="running", cycle=memory.cycle)
            validation = WorkspaceValidator(Path(memory.worktree or self.root), memory.task).validate()
            memory.current_fingerprint = validation.fingerprint
            logger.event(
                "validation.completed",
                stage="validation",
                status="passed" if validation.passed else "failed",
                cycle=memory.cycle,
                details=asdict(validation),
            )
            if not validation.passed:
                memory.unresolved_findings = [{"type": "validation", "message": value} for value in validation.errors]
                self.state.transition(memory, WorkflowState.CHANGES_REQUESTED)
            else:
                self.state.transition(memory, WorkflowState.TESTING)
            return
        if action is SupervisorAction.RUN_TESTS:
            logger.event("tests.started", stage="testing", status="running", cycle=memory.cycle)
            result = self.tests.run(Path(memory.worktree or self.root), memory.task)
            memory.test_results.append(asdict(result))
            memory.current_fingerprint = result.fingerprint
            logger.event(
                "tests.completed",
                stage="testing",
                status="passed" if result.passed else "failed",
                cycle=memory.cycle,
                details=asdict(result),
            )
            if result.passed:
                self.state.transition(memory, WorkflowState.REVIEWING)
            else:
                memory.unresolved_findings = [{"type": "test_failure", "stdout": result.stdout, "stderr": result.stderr}]
                self.state.transition(memory, WorkflowState.CHANGES_REQUESTED)
            return
        if action is SupervisorAction.REVIEW:
            result = self._invoke_role(AgentRole.REVIEWER, memory, self._review_context(memory), logger)
            review = self.executor.parse_review(result.raw_output, memory.current_fingerprint)
            logger.event(
                "review.completed", stage="review", status=review.decision.value,
                cycle=memory.cycle, details={"summary": review.summary},
            )
            memory.review_results.append(
                {
                    "decision": review.decision.value,
                    "reviewed_fingerprint": review.reviewed_fingerprint,
                    "findings": [asdict(value) for value in review.findings],
                    "summary": review.summary,
                }
            )
            if review.decision is ReviewDecision.APPROVED and review.reviewed_fingerprint == memory.current_fingerprint:
                memory.unresolved_findings = []
                self.state.transition(memory, WorkflowState.APPROVED)
            elif review.decision is ReviewDecision.CHANGES_REQUESTED:
                memory.unresolved_findings = [asdict(value) for value in review.findings]
                self.state.transition(memory, WorkflowState.CHANGES_REQUESTED)
            else:
                self.state.transition(memory, WorkflowState.NEEDS_INPUT)
            return
        if action is SupervisorAction.FINISH:
            self.state.transition(memory, WorkflowState.COMPLETED)
            logger.event(
                "workflow.completed", stage="workflow", status="local_only",
                cycle=memory.cycle, details={"state": memory.state.value, "artifacts": memory.artifacts},
            )
            return
        if action is SupervisorAction.DELIVER:
            if not deliver:
                raise ValidationError("Delivery was not authorized")
            self.state.transition(memory, WorkflowState.DELIVERING)
            logger.event("delivery.started", stage="delivery", status="running", cycle=memory.cycle)
            pr_url = self.delivery.deliver(memory)
            memory.artifacts.append(pr_url)
            self.state.transition(memory, WorkflowState.DELIVERED)
            logger.event(
                "workflow.completed", stage="delivery", status="delivered",
                cycle=memory.cycle, details={"state": memory.state.value, "artifacts": memory.artifacts},
            )
            if self.create_worktree and memory.worktree:
                try:
                    self.worktrees.remove_delivered(memory.task, Path(memory.worktree))
                    logger.event(
                        "worktree.removed", stage="cleanup", status="completed",
                        cycle=memory.cycle, details={"worktree": memory.worktree},
                    )
                except ValidationError as exc:
                    logger.event(
                        "worktree.retained", stage="cleanup", status="warning",
                        cycle=memory.cycle,
                        details={"worktree": memory.worktree, "reason": str(exc)},
                    )
            logger.event(
                "workflow.finished", stage="workflow", status="completed",
                cycle=memory.cycle, details={"state": memory.state.value},
            )
            return
        if action is SupervisorAction.REQUEST_INPUT:
            self.state.transition(memory, WorkflowState.NEEDS_INPUT)
            logger.event(
                "workflow.paused", stage="workflow", status="needs_input",
                cycle=memory.cycle, details={"findings": memory.unresolved_findings},
            )
            return
        raise ValidationError(f"Unsupported Supervisor action: {action.value}")

    def _invoke_role(
        self,
        role: AgentRole,
        memory: ExecutionMemory,
        request: dict,
        logger: EventLogger,
    ) -> AgentResult:
        logger.event("agent.started", stage=role.value, status="running", cycle=memory.cycle)
        try:
            result = self.executor.invoke_role(
                role, memory, request,
                progress=lambda event, status, details: logger.event(
                    event, stage=role.value, status=status,
                    cycle=memory.cycle, details=details,
                ),
            )
            self._assert_role_artifacts(role, memory)
        except (AgentExecutionError, ValidationError) as exc:
            logger.event(
                "agent.failed", stage=role.value, status="failed",
                cycle=memory.cycle, details={"error": str(exc)},
            )
            raise
        logger.event(
            "agent.finished", stage=role.value, status="completed",
            cycle=memory.cycle, details={"summary": result.summary},
        )
        return result

    @staticmethod
    def _assert_role_artifacts(role: AgentRole, memory: ExecutionMemory) -> None:
        if role not in (AgentRole.IMPLEMENTER, AgentRole.TEST_WRITER):
            return
        worktree = Path(memory.worktree or ".")
        boundary = memory.task.workspace.coding_dir if role is AgentRole.IMPLEMENTER else memory.task.workspace.test_dir
        expected = [path for path in memory.task.required_files if Path(path).is_relative_to(boundary)]
        missing = [path for path in expected if not (worktree / path).is_file()]
        if missing:
            names = ", ".join(missing)
            raise AgentExecutionError(
                f"Agent '{role.value}' returned before creating required artifact(s): {names}"
            )

    @staticmethod
    def _context(memory: ExecutionMemory) -> dict:
        return {
            "task": memory.task.to_dict(),
            "run_id": memory.run_id,
            "cycle": memory.cycle,
            "max_cycles": memory.max_cycles,
            "worktree": memory.worktree,
            "repository_context": memory.repository_context,
            "test_results": memory.test_results[-1:] if memory.test_results else [],
            "review_results": memory.review_results[-1:] if memory.review_results else [],
            "unresolved_findings": memory.unresolved_findings,
            "current_fingerprint": memory.current_fingerprint,
        }

    @classmethod
    def _review_context(cls, memory: ExecutionMemory) -> dict:
        """Supply the reviewer deterministic change evidence, not agent claims."""
        context = cls._context(memory)
        worktree = Path(memory.worktree or ".").resolve()
        changed_files = WorkspaceValidator(worktree, memory.task).changed_files()
        diff = subprocess.run(
            ["git", "diff", "--no-ext-diff", "--", *changed_files],
            cwd=worktree,
            capture_output=True,
            text=True,
            check=False,
        ).stdout
        untracked_contents: dict[str, str] = {}
        remaining = 200_000
        for relative in changed_files:
            path = worktree / relative
            if not path.is_file() or path.is_symlink() or path.stat().st_size > remaining:
                continue
            tracked = subprocess.run(
                ["git", "ls-files", "--error-unmatch", "--", relative],
                cwd=worktree,
                capture_output=True,
                check=False,
            ).returncode == 0
            if tracked:
                continue
            try:
                content = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            untracked_contents[relative] = content
            remaining -= len(content.encode("utf-8"))
        context["change_evidence"] = {
            "changed_files": changed_files,
            "tracked_diff": diff,
            "untracked_file_contents": untracked_contents,
        }
        return context

    @staticmethod
    def _agent_record(result) -> dict:
        value = asdict(result)
        value["role"] = result.role.value
        return value

    def _fail(self, memory: ExecutionMemory) -> None:
        if memory.state is WorkflowState.FAILED:
            return
        if WorkflowState.FAILED in self._allowed_targets(memory.state):
            self.state.transition(memory, WorkflowState.FAILED)

    @staticmethod
    def _allowed_targets(state: WorkflowState) -> set[WorkflowState]:
        from .state_store import ALLOWED_TRANSITIONS

        return ALLOWED_TRANSITIONS.get(state, set())
