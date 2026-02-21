"""Orchestrator: central coordination layer for the Data Journal system."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from shared.ai_client.client import AIClient, BudgetContext
from shared.ai_client.budget import BudgetManager, GlobalBudgetPool
from shared.models.agent import AgentPhase
from shared.models.events import Event, EventLog, EventType
from shared.models.project import ProjectStatus
from shared.utils.config import SystemConfig
from shared.utils.files import load_json, save_json
from shared.utils.logging import get_logger
from orchestrator.src.project_manager import ProjectManager
from agents.research.agent import ResearchAgent

logger = get_logger("orchestrator")


class Orchestrator:
    """Central orchestrator managing projects, agents, and budgets."""

    def __init__(self, root_dir: Path | None = None, config: SystemConfig | None = None):
        self.config = config or SystemConfig.load(root_dir)
        self.root_dir = self.config.root_dir

        # Sub-systems
        self.project_manager = ProjectManager(self.root_dir)
        self.budget_manager = BudgetManager(
            self.root_dir,
            GlobalBudgetPool(
                max_tokens=self.config.budget.global_pool.max_tokens,
                max_cost_usd=self.config.budget.global_pool.max_cost_usd,
            ),
        )
        self.event_log = EventLog(self.config.event_log_file)

        # Active agents
        self._agents: dict[str, ResearchAgent] = {}
        self._ai_client: AIClient | None = None

        # Load persisted state
        self._state_file = self.config.state_file
        self._load_state()

    # --- AI Client ---

    def set_ai_client(self, client: AIClient):
        """Set the AI client for agent operations."""
        self._ai_client = client

    def _get_ai_client(self) -> AIClient | None:
        """Get or create the AI client."""
        if self._ai_client is None:
            try:
                self._ai_client = AIClient(
                    default_model=self.config.ai_client.default_model,
                    max_retries=self.config.ai_client.anthropic.max_retries,
                    timeout_seconds=self.config.ai_client.anthropic.timeout_seconds,
                )
            except Exception as e:
                logger.warning("Could not create AI client: %s", e)
        return self._ai_client

    # --- Project Operations ---

    def add_topic(
        self,
        name: str,
        topic: str,
        description: str = "",
        research_questions: list[str] | None = None,
        data_sources: list[dict] | None = None,
        priority: str = "normal",
        budget: dict | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a new research project and allocate budget."""
        # Create project
        project = self.project_manager.create_project(
            name=name,
            topic=topic,
            description=description,
            research_questions=research_questions,
            data_sources=data_sources,
            priority=priority,
            budget=budget,
            tags=tags,
        )

        # Allocate budget
        budget_cfg = project.config.agent.budget
        budget_ctx = self.budget_manager.create_context(
            project_id=name,
            max_tokens=budget_cfg.max_tokens,
            max_api_calls=budget_cfg.max_api_calls,
            max_cost_usd=budget_cfg.max_cost_usd,
        )

        # Emit event
        self.event_log.emit(Event(
            event_type=EventType.PROJECT_CREATED,
            project_name=name,
            data={"topic": topic, "priority": priority},
        ))

        self._save_state()
        logger.info("Added topic: %s", name)

        return {
            "name": name,
            "topic": topic,
            "status": "created",
            "budget": budget_ctx.to_dict(),
        }

    def list_projects(self, status_filter: str | None = None) -> list[dict]:
        """List all projects with optional status filter."""
        return self.project_manager.list_projects(status_filter)

    def get_status(self, project_name: str) -> dict[str, Any]:
        """Get detailed status of a project including agent and budget info."""
        summary = self.project_manager.get_project_summary(project_name)
        budget_report = self.budget_manager.get_project_report(project_name)

        agent = self._agents.get(project_name)
        agent_info = None
        if agent:
            agent_info = {
                "agent_id": agent.state.agent_id,
                "phase": agent.state.phase.value,
                "progress": agent.state.progress_pct,
                "current_task": agent.state.current_task,
                "budget_usage": agent.state.budget_usage.to_dict(),
                "errors": agent.state.errors[-5:],  # Last 5 errors
            }

        return {
            **summary,
            "budget": budget_report,
            "agent": agent_info,
        }

    def start_agent(self, project_name: str) -> dict[str, Any]:
        """Spawn and start a research agent for a project."""
        if project_name in self._agents:
            return {"error": f"Agent already running for {project_name}"}

        # Check concurrent agent limit
        if len(self._agents) >= self.config.orchestrator.max_concurrent_agents:
            return {"error": f"Max concurrent agents ({self.config.orchestrator.max_concurrent_agents}) reached"}

        # Load project
        project = self.project_manager.load_project(project_name)

        # Ensure project is active
        if project.status == ProjectStatus.CREATED:
            self.project_manager.update_status(project_name, ProjectStatus.ACTIVE)
            self.event_log.emit(Event(
                event_type=EventType.PROJECT_STATE_CHANGED,
                project_name=project_name,
                data={"from": "created", "to": "active"},
            ))

        # Get budget context
        budget_ctx = self.budget_manager.get_context(project_name)

        # Create agent
        ai_client = self._get_ai_client()
        agent = ResearchAgent(
            project=project,
            ai_client=ai_client,
            budget_context=budget_ctx,
        )
        self._agents[project_name] = agent

        self.event_log.emit(Event(
            event_type=EventType.AGENT_STARTED,
            project_name=project_name,
            agent_id=agent.state.agent_id,
        ))

        self._save_state()
        logger.info("Started agent for: %s", project_name)

        return {
            "project": project_name,
            "agent_id": agent.state.agent_id,
            "status": "started",
        }

    def run_agent(self, project_name: str) -> dict[str, Any]:
        """Run the full research pipeline for a project's agent."""
        agent = self._agents.get(project_name)
        if not agent:
            # Auto-start
            start_result = self.start_agent(project_name)
            if "error" in start_result:
                return start_result
            agent = self._agents[project_name]

        try:
            result = agent.run_full_pipeline()

            self.event_log.emit(Event(
                event_type=EventType.AGENT_COMPLETED,
                project_name=project_name,
                agent_id=agent.state.agent_id,
                data={"result_summary": {k: str(v)[:200] for k, v in result.items()}},
            ))

            # Transition project to review
            try:
                self.project_manager.update_status(project_name, ProjectStatus.REVIEW)
                self.event_log.emit(Event(
                    event_type=EventType.REPORT_DRAFT_READY,
                    project_name=project_name,
                ))
            except ValueError:
                pass  # Status may already be in review

            return result

        except Exception as e:
            self.event_log.emit(Event(
                event_type=EventType.AGENT_ERROR,
                project_name=project_name,
                agent_id=agent.state.agent_id,
                data={"error": str(e)},
            ))
            return {"error": str(e)}

    def run_agent_phase(self, project_name: str, phase: str) -> dict[str, Any]:
        """Run a specific phase for a project's agent."""
        agent = self._agents.get(project_name)
        if not agent:
            start_result = self.start_agent(project_name)
            if "error" in start_result:
                return start_result
            agent = self._agents[project_name]

        try:
            agent_phase = AgentPhase(phase)
            return agent.run_phase(agent_phase)
        except Exception as e:
            return {"error": str(e)}

    # --- Review Operations ---

    def review(self, project_name: str) -> dict[str, Any]:
        """Get the review package for a project."""
        project = self.project_manager.load_project(project_name)
        report_dir = project.path / "report" / "drafts"

        if not report_dir.exists():
            return {"error": "No drafts available for review"}

        # Find latest draft
        versions = sorted(report_dir.iterdir(), reverse=True)
        if not versions:
            return {"error": "No drafts available for review"}

        latest = versions[0]
        whitepaper_path = latest / "whitepaper.md"
        quality_path = latest / "quality_report.yaml"

        result: dict[str, Any] = {
            "project": project_name,
            "status": project.status.value,
            "draft_version": latest.name,
        }

        if whitepaper_path.exists():
            result["whitepaper_path"] = str(whitepaper_path)
        if quality_path.exists():
            from shared.utils.files import load_yaml
            result["quality_report"] = load_yaml(quality_path)

        return result

    def approve(self, project_name: str) -> dict[str, Any]:
        """Approve a report and archive the project."""
        # Save final report
        project = self.project_manager.load_project(project_name)
        report_dir = project.path / "report" / "drafts"
        versions = sorted(report_dir.iterdir(), reverse=True) if report_dir.exists() else []

        if versions:
            latest = versions[0]
            meta_path = latest / "report_meta.json"
            if meta_path.exists():
                from shared.models.report import Report
                meta = load_json(meta_path)
                report = Report.from_dict(meta)
                composer = ReportComposer(project.path)
                composer.save_final(report)

        # Archive
        archive_path = self.project_manager.archive_project(project_name)

        # Release budget
        self.budget_manager.release_context(project_name)

        # Remove agent
        self._agents.pop(project_name, None)

        self.event_log.emit(Event(
            event_type=EventType.REPORT_APPROVED,
            project_name=project_name,
        ))
        self.event_log.emit(Event(
            event_type=EventType.PROJECT_ARCHIVED,
            project_name=project_name,
            data={"archive_path": str(archive_path)},
        ))

        self._save_state()
        logger.info("Approved and archived: %s", project_name)

        return {"project": project_name, "status": "archived", "path": str(archive_path)}

    def reject(self, project_name: str, feedback: str) -> dict[str, Any]:
        """Reject a report and send it back for revision."""
        self.project_manager.update_status(project_name, ProjectStatus.REVISION)

        self.event_log.emit(Event(
            event_type=EventType.REPORT_REVISION_REQUESTED,
            project_name=project_name,
            data={"feedback": feedback},
        ))

        # If agent exists, run revision
        agent = self._agents.get(project_name)
        if agent:
            try:
                return agent.revise(feedback)
            except Exception as e:
                return {"error": str(e), "feedback_saved": True}

        return {
            "project": project_name,
            "status": "revision",
            "feedback": feedback,
            "message": "Feedback recorded. Start the agent to apply revisions.",
        }

    # --- Budget Operations ---

    def set_budget(self, project_name: str, budget: dict) -> dict[str, Any]:
        """Update budget allocation for a project."""
        ctx = self.budget_manager.get_context(project_name)
        if ctx:
            if "max_tokens" in budget:
                ctx.max_tokens = budget["max_tokens"]
            if "max_api_calls" in budget:
                ctx.max_api_calls = budget["max_api_calls"]
            if "max_cost_usd" in budget:
                ctx.max_cost_usd = budget["max_cost_usd"]
            self.budget_manager.save_state()
            return ctx.to_dict()
        return {"error": "No budget context found for project"}

    def get_budget_report(self) -> dict[str, Any]:
        """Get the global budget report."""
        return self.budget_manager.get_global_report()

    # --- Agent Control ---

    def pause(self, project_name: str) -> dict[str, Any]:
        """Pause a project's agent."""
        agent = self._agents.get(project_name)
        if not agent:
            return {"error": "No agent running for project"}

        agent.save_state()
        self._agents.pop(project_name)

        self.event_log.emit(Event(
            event_type=EventType.AGENT_PAUSED,
            project_name=project_name,
            agent_id=agent.state.agent_id,
        ))

        return {"project": project_name, "status": "paused"}

    def resume(self, project_name: str) -> dict[str, Any]:
        """Resume a paused agent."""
        return self.start_agent(project_name)

    # --- State Persistence ---

    def _save_state(self):
        """Save orchestrator state."""
        state = {
            "active_agents": list(self._agents.keys()),
            "updated_at": datetime.utcnow().isoformat() + "Z",
        }
        save_json(self._state_file, state)
        self.budget_manager.save_state()

    def _load_state(self):
        """Load orchestrator state."""
        self.budget_manager.load_state()
        # Agent state is loaded when agents are started
