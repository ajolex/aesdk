"""Project lifecycle state machine."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from aesdk.core.errors import StateTransitionError


class ProjectState(str, Enum):
    NEW = "new"
    INITIALIZED = "initialized"
    PROPOSAL_RECEIVED = "proposal_received"
    VALIDATED = "validated"
    BLOCKED = "blocked"
    OVERRIDDEN = "overridden"
    EXECUTED = "executed"


@dataclass
class ProjectStateMachine:
    state: ProjectState = ProjectState.NEW

    def on_init(self) -> None:
        self._require(ProjectState.NEW)
        self.state = ProjectState.INITIALIZED

    def on_propose(self) -> None:
        if self.state not in {
            ProjectState.INITIALIZED,
            ProjectState.VALIDATED,
            ProjectState.EXECUTED,
            ProjectState.OVERRIDDEN,
            ProjectState.BLOCKED,
        }:
            raise StateTransitionError(f"Cannot propose in state '{self.state.value}'.")
        self.state = ProjectState.PROPOSAL_RECEIVED

    def on_validate(self, status: str) -> None:
        self._require(ProjectState.PROPOSAL_RECEIVED)
        if status == "block":
            self.state = ProjectState.BLOCKED
        else:
            self.state = ProjectState.VALIDATED

    def on_override(self) -> None:
        self._require(ProjectState.BLOCKED)
        self.state = ProjectState.OVERRIDDEN

    def on_execute(self) -> None:
        if self.state not in {ProjectState.VALIDATED, ProjectState.OVERRIDDEN}:
            raise StateTransitionError(
                f"Cannot execute in state '{self.state.value}'. Validate first or override."
            )
        self.state = ProjectState.EXECUTED

    def _require(self, expected: ProjectState) -> None:
        if self.state != expected:
            raise StateTransitionError(
                f"Invalid transition: expected '{expected.value}', got '{self.state.value}'."
            )
