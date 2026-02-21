"""Configuration loading and validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


def load_yaml(path: Path) -> dict:
    """Load a YAML file and return its contents as a dict."""
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(path) as f:
        return yaml.safe_load(f) or {}


def save_yaml(path: Path, data: dict):
    """Save a dict as a YAML file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)


@dataclass
class SchedulingConfig:
    strategy: str = "priority"
    tick_interval_seconds: int = 60


@dataclass
class PersistenceConfig:
    state_file: str = "orchestrator/state.json"
    event_log: str = "orchestrator/events.jsonl"


@dataclass
class OrchestratorConfig:
    max_concurrent_agents: int = 5
    scheduling: SchedulingConfig = field(default_factory=SchedulingConfig)
    persistence: PersistenceConfig = field(default_factory=PersistenceConfig)


@dataclass
class BudgetPoolConfig:
    max_tokens: int = 10_000_000
    max_cost_usd: float = 500.00


@dataclass
class DefaultBudgetConfig:
    max_tokens: int = 500_000
    max_api_calls: int = 200
    max_cost_usd: float = 25.00


@dataclass
class AlertsConfig:
    warn_at_percent: int = 75
    critical_at_percent: int = 90


@dataclass
class GlobalBudgetConfig:
    global_pool: BudgetPoolConfig = field(default_factory=BudgetPoolConfig)
    default_project: DefaultBudgetConfig = field(default_factory=DefaultBudgetConfig)
    alerts: AlertsConfig = field(default_factory=AlertsConfig)


@dataclass
class AnthropicConfig:
    api_key_env: str = "ANTHROPIC_API_KEY"
    max_retries: int = 3
    timeout_seconds: int = 120


@dataclass
class ModelRoutingConfig:
    planning: str = "claude-sonnet-4-20250514"
    drafting: str = "claude-sonnet-4-20250514"
    analysis: str = "claude-haiku-4-20250414"
    quality_check: str = "claude-sonnet-4-20250514"
    extraction: str = "claude-haiku-4-20250414"

    def get_model(self, task_type: str) -> str:
        return getattr(self, task_type, self.planning)


@dataclass
class AIClientConfig:
    default_provider: str = "anthropic"
    default_model: str = "claude-sonnet-4-20250514"
    anthropic: AnthropicConfig = field(default_factory=AnthropicConfig)
    model_routing: ModelRoutingConfig = field(default_factory=ModelRoutingConfig)


@dataclass
class CrawlingConfig:
    requests_per_second: float = 1.0
    burst_limit: int = 5
    cache_enabled: bool = True
    cache_ttl_hours: int = 24
    cache_max_size_mb: int = 500
    user_agent: str = "DataJournal-Research-Bot/1.0"
    timeout_seconds: int = 30
    max_retries: int = 3


@dataclass
class ReportDefaults:
    default_template: str = "academic_whitepaper"
    default_citation_format: str = "apa"
    min_abstract_words: int = 150
    min_body_words: int = 3000
    readability_grade_min: int = 12
    readability_grade_max: int = 16


@dataclass
class SystemConfig:
    """Top-level system configuration loaded from settings.yaml."""

    name: str = "Data Journal"
    version: str = "0.1.0"
    log_level: str = "INFO"
    log_format: str = "json"
    root_dir: Path = field(default_factory=lambda: Path("."))
    orchestrator: OrchestratorConfig = field(default_factory=OrchestratorConfig)
    budget: GlobalBudgetConfig = field(default_factory=GlobalBudgetConfig)
    ai_client: AIClientConfig = field(default_factory=AIClientConfig)
    crawling: CrawlingConfig = field(default_factory=CrawlingConfig)
    report: ReportDefaults = field(default_factory=ReportDefaults)

    @property
    def projects_active_dir(self) -> Path:
        return self.root_dir / "projects" / "active"

    @property
    def projects_archive_dir(self) -> Path:
        return self.root_dir / "projects" / "archive"

    @property
    def state_file(self) -> Path:
        return self.root_dir / self.orchestrator.persistence.state_file

    @property
    def event_log_file(self) -> Path:
        return self.root_dir / self.orchestrator.persistence.event_log

    @classmethod
    def load(cls, root_dir: Path | None = None) -> SystemConfig:
        """Load configuration from the project root's config/settings.yaml."""
        if root_dir is None:
            root_dir = Path.cwd()
        config_path = root_dir / "config" / "settings.yaml"
        if not config_path.exists():
            return cls(root_dir=root_dir)

        raw = load_yaml(config_path)
        sys_raw = raw.get("system", {})
        orch_raw = raw.get("orchestrator", {})
        budget_raw = raw.get("budget", {})
        ai_raw = raw.get("ai_client", {})
        crawl_raw = raw.get("crawling", {})
        report_raw = raw.get("report", {})

        sched_raw = orch_raw.get("scheduling", {})
        persist_raw = orch_raw.get("persistence", {})
        anthro_raw = ai_raw.get("anthropic", {})
        routing_raw = ai_raw.get("model_routing", {})
        pool_raw = budget_raw.get("global_pool", {})
        default_raw = budget_raw.get("default_project", {})
        alerts_raw = budget_raw.get("alerts", {})
        rate_raw = crawl_raw.get("rate_limit", {})
        cache_raw = crawl_raw.get("cache", {})

        return cls(
            name=sys_raw.get("name", "Data Journal"),
            version=sys_raw.get("version", "0.1.0"),
            log_level=sys_raw.get("log_level", "INFO"),
            log_format=sys_raw.get("log_format", "json"),
            root_dir=root_dir,
            orchestrator=OrchestratorConfig(
                max_concurrent_agents=orch_raw.get("max_concurrent_agents", 5),
                scheduling=SchedulingConfig(
                    strategy=sched_raw.get("strategy", "priority"),
                    tick_interval_seconds=sched_raw.get("tick_interval_seconds", 60),
                ),
                persistence=PersistenceConfig(
                    state_file=persist_raw.get("state_file", "orchestrator/state.json"),
                    event_log=persist_raw.get("event_log", "orchestrator/events.jsonl"),
                ),
            ),
            budget=GlobalBudgetConfig(
                global_pool=BudgetPoolConfig(
                    max_tokens=pool_raw.get("max_tokens", 10_000_000),
                    max_cost_usd=pool_raw.get("max_cost_usd", 500.00),
                ),
                default_project=DefaultBudgetConfig(
                    max_tokens=default_raw.get("max_tokens", 500_000),
                    max_api_calls=default_raw.get("max_api_calls", 200),
                    max_cost_usd=default_raw.get("max_cost_usd", 25.00),
                ),
                alerts=AlertsConfig(
                    warn_at_percent=alerts_raw.get("warn_at_percent", 75),
                    critical_at_percent=alerts_raw.get("critical_at_percent", 90),
                ),
            ),
            ai_client=AIClientConfig(
                default_provider=ai_raw.get("default_provider", "anthropic"),
                default_model=ai_raw.get("default_model", "claude-sonnet-4-20250514"),
                anthropic=AnthropicConfig(
                    api_key_env=anthro_raw.get("api_key_env", "ANTHROPIC_API_KEY"),
                    max_retries=anthro_raw.get("max_retries", 3),
                    timeout_seconds=anthro_raw.get("timeout_seconds", 120),
                ),
                model_routing=ModelRoutingConfig(
                    planning=routing_raw.get("planning", "claude-sonnet-4-20250514"),
                    drafting=routing_raw.get("drafting", "claude-sonnet-4-20250514"),
                    analysis=routing_raw.get("analysis", "claude-haiku-4-20250414"),
                    quality_check=routing_raw.get("quality_check", "claude-sonnet-4-20250514"),
                    extraction=routing_raw.get("extraction", "claude-haiku-4-20250414"),
                ),
            ),
            crawling=CrawlingConfig(
                requests_per_second=rate_raw.get("requests_per_second", 1.0),
                burst_limit=rate_raw.get("burst_limit", 5),
                cache_enabled=cache_raw.get("enabled", True),
                cache_ttl_hours=cache_raw.get("ttl_hours", 24),
                cache_max_size_mb=cache_raw.get("max_size_mb", 500),
                user_agent=crawl_raw.get("user_agent", "DataJournal-Research-Bot/1.0"),
                timeout_seconds=crawl_raw.get("timeout_seconds", 30),
                max_retries=crawl_raw.get("max_retries", 3),
            ),
            report=ReportDefaults(
                default_template=report_raw.get("default_template", "academic_whitepaper"),
                default_citation_format=report_raw.get("default_citation_format", "apa"),
                min_abstract_words=report_raw.get("min_abstract_words", 150),
                min_body_words=report_raw.get("min_body_words", 3000),
                readability_grade_min=report_raw.get("readability_grade_range", [12, 16])[0],
                readability_grade_max=report_raw.get("readability_grade_range", [12, 16])[1],
            ),
        )
