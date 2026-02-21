"""Event models for the orchestrator event system."""

from __future__ import annotations

import enum
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


class EventType(enum.Enum):
    # Project events
    PROJECT_CREATED = "project.created"
    PROJECT_STATE_CHANGED = "project.state_changed"
    PROJECT_ARCHIVED = "project.archived"

    # Agent events
    AGENT_STARTED = "agent.started"
    AGENT_PAUSED = "agent.paused"
    AGENT_COMPLETED = "agent.completed"
    AGENT_BUDGET_EXHAUSTED = "agent.budget_exhausted"
    AGENT_ERROR = "agent.error"

    # Report events
    REPORT_DRAFT_READY = "report.draft_ready"
    REPORT_APPROVED = "report.approved"
    REPORT_REVISION_REQUESTED = "report.revision_requested"

    # Budget events
    BUDGET_WARNING = "budget.warning"
    BUDGET_CRITICAL = "budget.critical"
    BUDGET_EXHAUSTED = "budget.exhausted"


@dataclass
class Event:
    event_type: EventType
    project_name: str = ""
    agent_id: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""

    def __post_init__(self):
        if isinstance(self.event_type, str):
            self.event_type = EventType(self.event_type)
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat() + "Z"

    def to_dict(self) -> dict:
        return {
            "event_type": self.event_type.value,
            "project_name": self.project_name,
            "agent_id": self.agent_id,
            "data": self.data,
            "timestamp": self.timestamp,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict) -> Event:
        return cls(
            event_type=data["event_type"],
            project_name=data.get("project_name", ""),
            agent_id=data.get("agent_id", ""),
            data=data.get("data", {}),
            timestamp=data.get("timestamp", ""),
        )


class EventLog:
    """Append-only event log backed by a JSONL file."""

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, event: Event):
        with open(self.path, "a") as f:
            f.write(event.to_json() + "\n")

    def read_all(self) -> list[Event]:
        if not self.path.exists():
            return []
        events = []
        with open(self.path) as f:
            for line in f:
                line = line.strip()
                if line:
                    events.append(Event.from_dict(json.loads(line)))
        return events

    def read_by_project(self, project_name: str) -> list[Event]:
        return [e for e in self.read_all() if e.project_name == project_name]

    def read_by_type(self, event_type: EventType) -> list[Event]:
        return [e for e in self.read_all() if e.event_type == event_type]
