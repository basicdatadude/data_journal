"""Project data models."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


class ProjectStatus(enum.Enum):
    CREATED = "created"
    ACTIVE = "active"
    REVIEW = "review"
    REVISION = "revision"
    ARCHIVED = "archived"


class Priority(enum.Enum):
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


@dataclass
class BudgetConfig:
    max_tokens: int = 500_000
    max_api_calls: int = 200
    max_cost_usd: float = 25.00


@dataclass
class AgentConfig:
    model: str = "claude-sonnet-4-20250514"
    temperature: float = 0.3
    max_tokens_per_call: int = 4096
    budget: BudgetConfig = field(default_factory=BudgetConfig)


@dataclass
class DataSourceConfig:
    source_type: str = "web_search"
    queries: list[str] = field(default_factory=list)


@dataclass
class ReportConfig:
    template: str = "academic_whitepaper"
    citation_format: str = "apa"
    target_length_words: int = 5000


@dataclass
class ProjectConfig:
    name: str
    topic: str
    description: str = ""
    status: ProjectStatus = ProjectStatus.CREATED
    priority: Priority = Priority.NORMAL
    created_date: str = ""
    completed_date: str = ""
    research_questions: list[str] = field(default_factory=list)
    agent: AgentConfig = field(default_factory=AgentConfig)
    data_sources: list[DataSourceConfig] = field(default_factory=list)
    report: ReportConfig = field(default_factory=ReportConfig)
    tags: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.created_date:
            self.created_date = datetime.now().isoformat()[:10]
        if isinstance(self.status, str):
            self.status = ProjectStatus(self.status)
        if isinstance(self.priority, str):
            self.priority = Priority(self.priority)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project": {
                "name": self.name,
                "topic": self.topic,
                "description": self.description,
                "status": self.status.value,
                "priority": self.priority.value,
                "created_date": self.created_date,
                "completed_date": self.completed_date,
                "research_questions": self.research_questions,
                "agent": {
                    "model": self.agent.model,
                    "temperature": self.agent.temperature,
                    "max_tokens_per_call": self.agent.max_tokens_per_call,
                    "budget": {
                        "max_tokens": self.agent.budget.max_tokens,
                        "max_api_calls": self.agent.budget.max_api_calls,
                        "max_cost_usd": self.agent.budget.max_cost_usd,
                    },
                },
                "data_sources": [
                    {"type": ds.source_type, "queries": ds.queries}
                    for ds in self.data_sources
                ],
                "report": {
                    "template": self.report.template,
                    "citation_format": self.report.citation_format,
                    "target_length_words": self.report.target_length_words,
                },
                "tags": self.tags,
            }
        }

    @classmethod
    def from_dict(cls, data: dict) -> ProjectConfig:
        proj = data.get("project", data)
        agent_data = proj.get("agent", {})
        budget_data = agent_data.get("budget", {})
        sources_data = proj.get("data_sources", [])
        report_data = proj.get("report", {})

        return cls(
            name=proj["name"],
            topic=proj.get("topic", ""),
            description=proj.get("description", ""),
            status=proj.get("status", "created"),
            priority=proj.get("priority", "normal"),
            created_date=proj.get("created_date", ""),
            completed_date=proj.get("completed_date", ""),
            research_questions=proj.get("research_questions", []),
            agent=AgentConfig(
                model=agent_data.get("model", "claude-sonnet-4-20250514"),
                temperature=agent_data.get("temperature", 0.3),
                max_tokens_per_call=agent_data.get("max_tokens_per_call", 4096),
                budget=BudgetConfig(
                    max_tokens=budget_data.get("max_tokens", 500_000),
                    max_api_calls=budget_data.get("max_api_calls", 200),
                    max_cost_usd=budget_data.get("max_cost_usd", 25.00),
                ),
            ),
            data_sources=[
                DataSourceConfig(
                    source_type=ds.get("type", "web_search"),
                    queries=ds.get("queries", []),
                )
                for ds in sources_data
            ],
            report=ReportConfig(
                template=report_data.get("template", "academic_whitepaper"),
                citation_format=report_data.get("citation_format", "apa"),
                target_length_words=report_data.get("target_length_words", 5000),
            ),
            tags=proj.get("tags", []),
        )


@dataclass
class Project:
    config: ProjectConfig
    path: Path = field(default_factory=lambda: Path("."))

    @property
    def name(self) -> str:
        return self.config.name

    @property
    def status(self) -> ProjectStatus:
        return self.config.status

    @status.setter
    def status(self, value: ProjectStatus):
        self.config.status = value

    @property
    def data_raw_dir(self) -> Path:
        return self.path / "data" / "raw"

    @property
    def data_processed_dir(self) -> Path:
        return self.path / "data" / "processed"

    @property
    def analysis_dir(self) -> Path:
        return self.path / "analysis"

    @property
    def report_dir(self) -> Path:
        return self.path / "report"

    @property
    def logs_dir(self) -> Path:
        return self.path / "logs"

    @property
    def references_dir(self) -> Path:
        return self.path / "references"
