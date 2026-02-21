"""Agent state models."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


class AgentPhase(enum.Enum):
    IDLE = "idle"
    INITIALIZE = "initialize"
    PLAN = "plan"
    COLLECT = "collect"
    ANALYZE = "analyze"
    DRAFT = "draft"
    SUBMIT = "submit"
    REVISE = "revise"
    DONE = "done"


@dataclass
class AgentMemory:
    """Working memory for a research agent."""

    research_plan: dict[str, Any] = field(default_factory=dict)
    findings: list[dict[str, Any]] = field(default_factory=list)
    decisions: list[dict[str, Any]] = field(default_factory=list)
    iteration_history: list[dict[str, Any]] = field(default_factory=list)

    def add_finding(self, finding: str, source: str = "", confidence: float = 0.5):
        self.findings.append({
            "finding": finding,
            "source": source,
            "confidence": confidence,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        })

    def add_decision(self, decision: str, rationale: str = ""):
        self.decisions.append({
            "decision": decision,
            "rationale": rationale,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        })

    def to_dict(self) -> dict:
        return {
            "research_plan": self.research_plan,
            "findings": self.findings,
            "decisions": self.decisions,
            "iteration_history": self.iteration_history,
        }

    @classmethod
    def from_dict(cls, data: dict) -> AgentMemory:
        return cls(
            research_plan=data.get("research_plan", {}),
            findings=data.get("findings", []),
            decisions=data.get("decisions", []),
            iteration_history=data.get("iteration_history", []),
        )


@dataclass
class BudgetUsage:
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_api_calls: int = 0
    estimated_cost_usd: float = 0.0

    @property
    def total_tokens(self) -> int:
        return self.total_input_tokens + self.total_output_tokens

    def to_dict(self) -> dict:
        return {
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_api_calls": self.total_api_calls,
            "estimated_cost_usd": round(self.estimated_cost_usd, 6),
            "total_tokens": self.total_tokens,
        }

    @classmethod
    def from_dict(cls, data: dict) -> BudgetUsage:
        return cls(
            total_input_tokens=data.get("total_input_tokens", 0),
            total_output_tokens=data.get("total_output_tokens", 0),
            total_api_calls=data.get("total_api_calls", 0),
            estimated_cost_usd=data.get("estimated_cost_usd", 0.0),
        )


@dataclass
class AgentState:
    agent_id: str = ""
    project_name: str = ""
    phase: AgentPhase = AgentPhase.IDLE
    memory: AgentMemory = field(default_factory=AgentMemory)
    budget_usage: BudgetUsage = field(default_factory=BudgetUsage)
    current_task: str = ""
    progress_pct: float = 0.0
    errors: list[str] = field(default_factory=list)
    started_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        if isinstance(self.phase, str):
            self.phase = AgentPhase(self.phase)
        if not self.started_at:
            self.started_at = datetime.utcnow().isoformat() + "Z"
        self.updated_at = datetime.utcnow().isoformat() + "Z"

    def transition(self, new_phase: AgentPhase):
        self.phase = new_phase
        self.updated_at = datetime.utcnow().isoformat() + "Z"

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "project_name": self.project_name,
            "phase": self.phase.value,
            "memory": self.memory.to_dict(),
            "budget_usage": self.budget_usage.to_dict(),
            "current_task": self.current_task,
            "progress_pct": self.progress_pct,
            "errors": self.errors,
            "started_at": self.started_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> AgentState:
        return cls(
            agent_id=data.get("agent_id", ""),
            project_name=data.get("project_name", ""),
            phase=data.get("phase", "idle"),
            memory=AgentMemory.from_dict(data.get("memory", {})),
            budget_usage=BudgetUsage.from_dict(data.get("budget_usage", {})),
            current_task=data.get("current_task", ""),
            progress_pct=data.get("progress_pct", 0.0),
            errors=data.get("errors", []),
            started_at=data.get("started_at", ""),
            updated_at=data.get("updated_at", ""),
        )
