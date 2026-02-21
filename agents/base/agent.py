"""Base agent class with lifecycle management, budget awareness, and state persistence."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from shared.ai_client.client import AIClient, BudgetContext, BudgetStatus, BudgetExhaustedError
from shared.models.agent import AgentPhase, AgentMemory, AgentState, BudgetUsage
from shared.models.project import Project
from shared.utils.files import save_json, load_json
from shared.utils.logging import ProjectLogger


class BaseAgent(ABC):
    """Abstract base agent with lifecycle management.

    Subclasses implement the phase-specific methods:
    initialize(), plan(), execute(), report(), reflect().
    """

    def __init__(
        self,
        project: Project,
        ai_client: AIClient | None = None,
        budget_context: BudgetContext | None = None,
    ):
        self.project = project
        self.ai_client = ai_client
        self.budget_context = budget_context
        self.state = AgentState(
            agent_id=f"agent-{uuid.uuid4().hex[:8]}",
            project_name=project.name,
        )
        self.logger = ProjectLogger(
            project.name,
            project.logs_dir,
        )
        self._state_file = project.path / "logs" / "agent_state.json"

    # --- Lifecycle Methods ---

    @abstractmethod
    def initialize(self) -> dict[str, Any]:
        """Set up the agent: load existing data, configure working context.

        Returns a summary of initialization.
        """

    @abstractmethod
    def plan(self) -> dict[str, Any]:
        """Create or update the research plan.

        Returns the plan as a dict.
        """

    @abstractmethod
    def collect(self) -> dict[str, Any]:
        """Execute data collection according to the plan.

        Returns a summary of collected data.
        """

    @abstractmethod
    def analyze(self) -> dict[str, Any]:
        """Run analyses on collected data.

        Returns analysis results summary.
        """

    @abstractmethod
    def draft(self) -> dict[str, Any]:
        """Draft the whitepaper report.

        Returns the report status.
        """

    @abstractmethod
    def submit(self) -> dict[str, Any]:
        """Submit the report for review.

        Returns submission details.
        """

    @abstractmethod
    def revise(self, feedback: str) -> dict[str, Any]:
        """Revise the report based on feedback.

        Returns revision details.
        """

    # --- State Management ---

    def transition(self, phase: AgentPhase):
        """Transition to a new phase, updating state and logging."""
        old_phase = self.state.phase
        self.state.transition(phase)
        self.logger.info(f"Phase transition: {old_phase.value} → {phase.value}")
        self.save_state()

    def save_state(self):
        """Persist agent state to disk."""
        save_json(self._state_file, self.state.to_dict())

    def load_state(self) -> bool:
        """Load agent state from disk. Returns True if state was found."""
        data = load_json(self._state_file)
        if data:
            self.state = AgentState.from_dict(data)
            self.logger.info(f"Resumed state: phase={self.state.phase.value}")
            return True
        return False

    # --- Budget ---

    def check_budget(self) -> BudgetStatus:
        """Check remaining budget before making an AI call."""
        if self.budget_context is None:
            return BudgetStatus.HEALTHY
        status = self.budget_context.status
        if status == BudgetStatus.CRITICAL:
            self.logger.warning(
                f"Budget critical: {self.budget_context.cost_usage_pct:.1f}% used"
            )
        return status

    def ai_generate(
        self,
        prompt: str,
        system: str | None = None,
        task: str = "",
        **kwargs,
    ) -> str:
        """Make an AI call with automatic budget checking and logging.

        Raises BudgetExhaustedError if budget is exceeded.
        Returns the generated text.
        """
        if self.ai_client is None:
            self.logger.warning("No AI client configured — returning placeholder")
            return f"[AI response placeholder for: {task or 'unknown task'}]"

        status = self.check_budget()
        if status == BudgetStatus.EXHAUSTED:
            self.logger.error("Budget exhausted, cannot make AI call")
            raise BudgetExhaustedError(f"Budget exhausted for {self.project.name}")

        response = self.ai_client.generate(
            prompt=prompt,
            system=system,
            budget_context=self.budget_context,
            task=task,
            project=self.project.name,
            **kwargs,
        )

        # Update agent's budget tracking
        self.state.budget_usage.total_input_tokens += response.input_tokens
        self.state.budget_usage.total_output_tokens += response.output_tokens
        self.state.budget_usage.total_api_calls += 1
        self.state.budget_usage.estimated_cost_usd += response.estimated_cost_usd

        return response.text

    # --- Execution ---

    def run_phase(self, phase: AgentPhase) -> dict[str, Any]:
        """Execute a specific phase."""
        self.transition(phase)

        phase_methods = {
            AgentPhase.INITIALIZE: self.initialize,
            AgentPhase.PLAN: self.plan,
            AgentPhase.COLLECT: self.collect,
            AgentPhase.ANALYZE: self.analyze,
            AgentPhase.DRAFT: self.draft,
            AgentPhase.SUBMIT: self.submit,
        }

        method = phase_methods.get(phase)
        if method is None:
            raise ValueError(f"No method for phase: {phase.value}")

        try:
            result = method()
            self.save_state()
            return result
        except BudgetExhaustedError:
            self.logger.error("Budget exhausted during %s phase", phase.value)
            self.state.errors.append(f"Budget exhausted during {phase.value}")
            self.save_state()
            raise
        except Exception as e:
            self.logger.error("Error in %s phase: %s", phase.value, e)
            self.state.errors.append(f"Error in {phase.value}: {str(e)}")
            self.save_state()
            raise

    def run_full_pipeline(self) -> dict[str, Any]:
        """Run the full research pipeline: initialize → plan → collect → analyze → draft → submit."""
        results: dict[str, Any] = {}

        phases = [
            AgentPhase.INITIALIZE,
            AgentPhase.PLAN,
            AgentPhase.COLLECT,
            AgentPhase.ANALYZE,
            AgentPhase.DRAFT,
            AgentPhase.SUBMIT,
        ]

        for phase in phases:
            try:
                result = self.run_phase(phase)
                results[phase.value] = result
            except BudgetExhaustedError:
                results[phase.value] = {"error": "budget_exhausted"}
                break
            except Exception as e:
                results[phase.value] = {"error": str(e)}
                self.logger.error("Pipeline stopped at %s: %s", phase.value, e)
                break

        self.transition(AgentPhase.DONE if not self.state.errors else AgentPhase.IDLE)
        return results
