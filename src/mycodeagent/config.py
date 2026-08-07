"""Load MyCodeAgent and Omnigent role configuration from TOML."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

from .errors import ConfigurationError
from .models import AgentRole, AgentRoleConfig


@dataclass(frozen=True)
class WorkflowConfig:
    harness: str
    model: str
    effort: str
    time_limit_seconds: int
    max_cycles: int
    role_configs: dict[AgentRole, AgentRoleConfig]

    def role(self, role: AgentRole) -> AgentRoleConfig:
        try:
            return self.role_configs[role]
        except KeyError as exc:
            raise ConfigurationError(f"Missing configuration for role '{role.value}'") from exc


def load_workflow_config(path: Path) -> WorkflowConfig:
    if not path.exists():
        raise ConfigurationError(f"Runtime configuration does not exist: {path}")
    with path.open("rb") as stream:
        data = tomllib.load(stream)

    defaults = data.get("defaults", data)
    required = ("harness", "model", "effort", "time_limit_seconds")
    missing = [name for name in required if not defaults.get(name)]
    if missing:
        raise ConfigurationError(f"Missing runtime setting(s): {', '.join(missing)}")

    workflow_data = data.get("workflow", {})
    max_cycles = int(workflow_data.get("max_cycles", data.get("max_cycles", 5)))
    if max_cycles != 5:
        raise ConfigurationError("MyCodeAgent requires max_cycles = 5")

    role_data = data.get("agents", {})
    role_configs: dict[AgentRole, AgentRoleConfig] = {}
    for role in AgentRole:
        override = role_data.get(role.value, {})
        read_only_default = role in (AgentRole.EXPLORER, AgentRole.REVIEWER)
        role_configs[role] = AgentRoleConfig(
            role=role,
            harness=str(override.get("harness", defaults["harness"])),
            model=str(override.get("model", defaults["model"])),
            effort=str(override.get("effort", defaults["effort"])),
            timeout_seconds=int(override.get("timeout_seconds", defaults["time_limit_seconds"])),
            read_only=bool(override.get("read_only", read_only_default)),
            write_scope=override.get("write_scope"),
        )

    return WorkflowConfig(
        harness=str(defaults["harness"]),
        model=str(defaults["model"]),
        effort=str(defaults["effort"]),
        time_limit_seconds=int(defaults["time_limit_seconds"]),
        max_cycles=max_cycles,
        role_configs=role_configs,
    )
