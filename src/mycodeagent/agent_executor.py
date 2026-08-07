"""Invoke Supervisor and specialized roles through the Omnigent meta-harness."""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

from .config import WorkflowConfig
from .errors import AgentExecutionError
from .models import (
    ActionDecision,
    AgentResult,
    AgentRole,
    ExecutionMemory,
    ReviewDecision,
    ReviewFinding,
    ReviewResult,
    SupervisorAction,
)

JSON_OBJECT = re.compile(r"\{.*\}", re.DOTALL)

ACTION_ROLES: dict[SupervisorAction, AgentRole] = {
    SupervisorAction.EXPLORE: AgentRole.EXPLORER,
    SupervisorAction.IMPLEMENT: AgentRole.IMPLEMENTER,
    SupervisorAction.WRITE_TESTS: AgentRole.TEST_WRITER,
    SupervisorAction.REVIEW: AgentRole.REVIEWER,
    SupervisorAction.REMEDIATE: AgentRole.IMPLEMENTER,
}

TRANSIENT_RUNNER_ERRORS = (
    "runner disconnected unexpectedly",
    "tunnel closed before request completed",
    "ping timeout",
)
MAX_AGENT_ATTEMPTS = 2


class OmnigentAgentExecutor:
    def __init__(self, repository_root: Path, config: WorkflowConfig, agents_dir: Path) -> None:
        self.repository_root = repository_root
        self.config = config
        self.agents_dir = agents_dir

    def supervisor_decision(
        self,
        memory: ExecutionMemory,
        available_actions: tuple[SupervisorAction, ...],
    ) -> ActionDecision:
        context = {
            "execution_memory": memory.to_dict(),
            "available_actions": [action.value for action in available_actions],
            "instruction": (
                "Return exactly one JSON object with action and concise rationale. "
                "Select only an available action. Do not execute the action yourself."
            ),
        }
        output = self._run_agent(
            self.agents_dir / "supervisor.yaml",
            harness=self.config.harness,
            model=self.config.model,
            effort=self.config.effort,
            timeout=self.config.time_limit_seconds,
            prompt=json.dumps(context, ensure_ascii=False),
            cwd=Path(memory.worktree) if memory.worktree else self.repository_root,
        )
        return self.parse_supervisor_decision(output, available_actions)

    @staticmethod
    def parse_supervisor_decision(
        output: str,
        available_actions: tuple[SupervisorAction, ...],
    ) -> ActionDecision:
        """Validate a supervisor action and derive its role deterministically.

        Omnigent may identify its supervising session as ``main``. That provider
        identity is deliberately ignored: only MyCodeAgent's selected action
        determines which specialized agent role, if any, will execute next.
        """
        payload = OmnigentAgentExecutor._json(output)
        try:
            action = SupervisorAction(str(payload["action"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise AgentExecutionError(f"Supervisor returned an invalid action: {payload}") from exc
        if action not in available_actions:
            raise AgentExecutionError(f"Supervisor selected disallowed action '{action.value}'")
        role = ACTION_ROLES.get(action)
        return ActionDecision(action=action, role=role, rationale=str(payload.get("rationale", "")))

    def invoke_role(self, role: AgentRole, memory: ExecutionMemory, request: dict) -> AgentResult:
        runtime = self.config.role(role)
        output = self._run_agent(
            self.agents_dir / f"{role.value}.yaml",
            harness=runtime.harness,
            model=runtime.model,
            effort=runtime.effort,
            timeout=runtime.timeout_seconds,
            prompt=json.dumps(request, ensure_ascii=False),
            cwd=Path(memory.worktree) if memory.worktree else self.repository_root,
        )
        return AgentResult(role=role, status="completed", summary=output[-2000:], raw_output=output)

    @staticmethod
    def parse_review(output: str, fingerprint: str) -> ReviewResult:
        try:
            payload = OmnigentAgentExecutor._json(output)
            decision = ReviewDecision(str(payload.get("decision", "")).lower())
            findings = tuple(
                ReviewFinding(
                    finding_id=str(item.get("finding_id", f"R{index}")),
                    severity=str(item.get("severity", "blocking")),
                    explanation=str(item.get("explanation", "")),
                    recommended_fix=str(item.get("recommended_fix", "")),
                    requirement=str(item.get("requirement", "")),
                    file=item.get("file"),
                    line=item.get("line"),
                )
                for index, item in enumerate(payload.get("findings", []), start=1)
                if isinstance(item, dict)
            )
            if decision is ReviewDecision.CHANGES_REQUESTED and not findings:
                raise ValueError("CHANGES_REQUESTED requires findings")
            return ReviewResult(decision, fingerprint, findings, str(payload.get("summary", "")))
        except (AgentExecutionError, ValueError, TypeError):
            pass
        upper = output.upper()
        if "CHANGES_REQUESTED" in upper:
            findings = (
                ReviewFinding(
                    finding_id="REVIEW-OUTPUT",
                    severity="blocking",
                    explanation=output.strip(),
                    recommended_fix="Address the structured reviewer findings.",
                ),
            )
            return ReviewResult(ReviewDecision.CHANGES_REQUESTED, fingerprint, findings, output.strip())
        if re.search(r"\bAPPROVED\b", upper):
            return ReviewResult(ReviewDecision.APPROVED, fingerprint, (), output.strip())
        return ReviewResult(ReviewDecision.BLOCKED, fingerprint, (), output.strip())

    def _run_agent(
        self,
        definition: Path,
        *,
        harness: str,
        model: str,
        effort: str,
        timeout: int,
        prompt: str,
        cwd: Path,
    ) -> str:
        if not definition.exists():
            raise AgentExecutionError(f"Agent definition does not exist: {definition}")
        source = definition.read_text(encoding="utf-8")
        rendered = (
            source.replace("${AGENT_HARNESS}", harness)
            .replace("${AGENT_MODEL}", model)
            .replace("${AGENT_EFFORT}", effort)
        )
        environment = os.environ.copy()
        omnigent_executable = environment.get("MYCODEAGENT_OMNIGENT_EXECUTABLE", "omnigent")
        with tempfile.TemporaryDirectory(prefix="mycodeagent-agent-") as directory:
            path = Path(directory) / definition.name
            path.write_text(rendered, encoding="utf-8")
            for attempt in range(1, MAX_AGENT_ATTEMPTS + 1):
                try:
                    result = subprocess.run(
                        [omnigent_executable, "run", str(path), "--harness", harness, "--model", model, "-p", prompt],
                        cwd=cwd,
                        env=environment,
                        capture_output=True,
                        text=True,
                        timeout=timeout,
                        check=False,
                    )
                except subprocess.TimeoutExpired as exc:
                    raise AgentExecutionError(f"Agent '{definition.stem}' exceeded {timeout} seconds") from exc
                output = "\n".join(value for value in (result.stdout, result.stderr) if value).strip()
                if result.returncode == 0:
                    return output
                transient = any(value in output.lower() for value in TRANSIENT_RUNNER_ERRORS)
                if not transient or attempt == MAX_AGENT_ATTEMPTS:
                    raise AgentExecutionError(
                        f"Agent '{definition.stem}' failed with exit {result.returncode} "
                        f"after {attempt} attempt(s): {output[-2000:]}"
                    )
        raise AgentExecutionError(f"Agent '{definition.stem}' did not produce a result")

    @staticmethod
    def _json(output: str) -> dict:
        candidates = [output.strip()]
        match = JSON_OBJECT.search(output)
        if match:
            candidates.append(match.group(0))
        for candidate in candidates:
            try:
                value = json.loads(candidate)
                if isinstance(value, dict):
                    return value
            except json.JSONDecodeError:
                continue
        raise AgentExecutionError(f"Agent did not return valid JSON: {output[-1000:]}")
