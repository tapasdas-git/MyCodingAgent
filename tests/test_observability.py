import json

from mycodeagent.observability import EventLogger, TraceContext


def test_event_is_written_to_run_and_task_traces_with_correlation(tmp_path):
    trace = TraceContext("run-1", "TASK-108", "trace-1")
    logger = EventLogger(tmp_path, trace)

    logger.event(
        "tests.completed", stage="testing", status="passed", cycle=1,
        details={"passed": True},
    )

    run_records = [json.loads(line) for line in logger.path.read_text().splitlines()]
    task_records = [json.loads(line) for line in logger.task_path.read_text().splitlines()]
    assert run_records == task_records
    assert run_records[0]["schema"] == "mycodeagent.event.v1"
    assert run_records[0]["run_id"] == "run-1"
    assert run_records[0]["task_id"] == "TASK-108"
    assert run_records[0]["trace_id"] == "trace-1"
    assert run_records[0]["cycle"] == 1


def test_task_trace_appends_across_runs_and_redacts_secrets(tmp_path):
    first = EventLogger(tmp_path, TraceContext("run-1", "TASK-108", "trace-1"))
    second = EventLogger(tmp_path, TraceContext("run-2", "TASK-108", "trace-2"))
    first.event(
        "agent.started", stage="implementer", status="running",
        details={"token": "sensitive", "nested": {"message": "password=hidden"}},
    )
    second.event("agent.finished", stage="implementer", status="passed")

    records = [json.loads(line) for line in first.task_path.read_text().splitlines()]
    assert [record["run_id"] for record in records] == ["run-1", "run-2"]
    assert records[0]["details"]["token"] == "[REDACTED]"
    assert records[0]["details"]["nested"]["message"] == "password=[REDACTED]"
    assert first.task_path.stat().st_mode & 0o777 == 0o600
    assert first.path.stat().st_mode & 0o777 == 0o600


def test_artifacts_are_redacted_and_owner_only(tmp_path):
    logger = EventLogger(tmp_path, TraceContext("run-1", "TASK-108", "trace-1"))
    artifact = logger.artifact("agent-output.txt", "authorization: Bearer private-value\n")

    assert artifact.read_text() == "authorization=[REDACTED]\n"
    assert artifact.stat().st_mode & 0o777 == 0o600
