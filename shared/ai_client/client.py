"""Unified AI client with budget tracking and model routing."""

from __future__ import annotations

import enum
import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from shared.utils.logging import get_logger

logger = get_logger("ai_client")


class BudgetStatus(enum.Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    EXHAUSTED = "exhausted"


class BudgetExhaustedError(Exception):
    pass


# Model pricing (per 1K tokens)
MODEL_PRICING = {
    "claude-opus-4-20250514": {"input": 0.015, "output": 0.075},
    "claude-sonnet-4-20250514": {"input": 0.003, "output": 0.015},
    "claude-haiku-4-20250414": {"input": 0.00025, "output": 0.00125},
}


@dataclass
class AIResponse:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0
    model: str = ""
    latency_ms: int = 0
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat() + "Z"


@dataclass
class UsageReport:
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_api_calls: int = 0
    total_cost_usd: float = 0.0
    calls_by_model: dict[str, int] = field(default_factory=dict)
    calls_by_task: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_api_calls": self.total_api_calls,
            "total_cost_usd": round(self.total_cost_usd, 6),
            "calls_by_model": self.calls_by_model,
            "calls_by_task": self.calls_by_task,
        }


@dataclass
class BudgetContext:
    project_id: str
    max_tokens: int = 500_000
    max_api_calls: int = 200
    max_cost_usd: float = 25.00
    warn_at_percent: int = 75
    critical_at_percent: int = 90
    # Current usage (updated by the client)
    used_tokens: int = 0
    used_api_calls: int = 0
    used_cost_usd: float = 0.0

    @property
    def remaining_tokens(self) -> int:
        return max(0, self.max_tokens - self.used_tokens)

    @property
    def remaining_api_calls(self) -> int:
        return max(0, self.max_api_calls - self.used_api_calls)

    @property
    def remaining_cost_usd(self) -> float:
        return max(0.0, self.max_cost_usd - self.used_cost_usd)

    @property
    def token_usage_pct(self) -> float:
        if self.max_tokens <= 0:
            return 100.0
        return (self.used_tokens / self.max_tokens) * 100

    @property
    def cost_usage_pct(self) -> float:
        if self.max_cost_usd <= 0:
            return 100.0
        return (self.used_cost_usd / self.max_cost_usd) * 100

    @property
    def status(self) -> BudgetStatus:
        pct = max(self.token_usage_pct, self.cost_usage_pct)
        if pct >= 100 or self.used_api_calls >= self.max_api_calls:
            return BudgetStatus.EXHAUSTED
        if pct >= self.critical_at_percent:
            return BudgetStatus.CRITICAL
        if pct >= self.warn_at_percent:
            return BudgetStatus.WARNING
        return BudgetStatus.HEALTHY

    def to_dict(self) -> dict:
        return {
            "project_id": self.project_id,
            "max_tokens": self.max_tokens,
            "max_api_calls": self.max_api_calls,
            "max_cost_usd": self.max_cost_usd,
            "used_tokens": self.used_tokens,
            "used_api_calls": self.used_api_calls,
            "used_cost_usd": round(self.used_cost_usd, 6),
            "remaining_tokens": self.remaining_tokens,
            "remaining_cost_usd": round(self.remaining_cost_usd, 6),
            "status": self.status.value,
        }

    @classmethod
    def from_dict(cls, data: dict) -> BudgetContext:
        return cls(
            project_id=data.get("project_id", ""),
            max_tokens=data.get("max_tokens", 500_000),
            max_api_calls=data.get("max_api_calls", 200),
            max_cost_usd=data.get("max_cost_usd", 25.00),
            warn_at_percent=data.get("warn_at_percent", 75),
            critical_at_percent=data.get("critical_at_percent", 90),
            used_tokens=data.get("used_tokens", 0),
            used_api_calls=data.get("used_api_calls", 0),
            used_cost_usd=data.get("used_cost_usd", 0.0),
        )


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate cost in USD for a given model and token counts."""
    pricing = MODEL_PRICING.get(model, MODEL_PRICING["claude-sonnet-4-20250514"])
    return (input_tokens / 1000) * pricing["input"] + (output_tokens / 1000) * pricing["output"]


class AIClient:
    """Unified AI service client with budget tracking and retry logic."""

    def __init__(
        self,
        default_model: str = "claude-sonnet-4-20250514",
        max_retries: int = 3,
        timeout_seconds: int = 120,
        log_file: Path | None = None,
        api_key: str | None = None,
        api_key_env: str = "ANTHROPIC_API_KEY",
    ):
        self.default_model = default_model
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds
        self.log_file = log_file
        self._api_key = api_key or os.environ.get(api_key_env, "")
        self._usage = UsageReport()
        self._client = None

    def _get_client(self):
        """Lazy-initialize the Anthropic client."""
        if self._client is None:
            try:
                import anthropic
                self._client = anthropic.Anthropic(
                    api_key=self._api_key,
                    timeout=self.timeout_seconds,
                )
            except ImportError:
                raise ImportError(
                    "anthropic package is required. Install with: pip install anthropic"
                )
        return self._client

    def check_budget(self, budget_context: BudgetContext | None) -> BudgetStatus:
        """Check the current budget status before making a call."""
        if budget_context is None:
            return BudgetStatus.HEALTHY
        return budget_context.status

    def _update_budget(
        self,
        budget_context: BudgetContext | None,
        input_tokens: int,
        output_tokens: int,
        cost: float,
    ):
        """Update budget context after a successful call."""
        if budget_context is None:
            return
        budget_context.used_tokens += input_tokens + output_tokens
        budget_context.used_api_calls += 1
        budget_context.used_cost_usd += cost

    def _log_call(
        self,
        model: str,
        task: str,
        project: str,
        input_tokens: int,
        output_tokens: int,
        cost: float,
        latency_ms: int,
        status: str,
    ):
        """Log an API call to the usage log."""
        self._usage.total_input_tokens += input_tokens
        self._usage.total_output_tokens += output_tokens
        self._usage.total_api_calls += 1
        self._usage.total_cost_usd += cost
        self._usage.calls_by_model[model] = self._usage.calls_by_model.get(model, 0) + 1
        if task:
            self._usage.calls_by_task[task] = self._usage.calls_by_task.get(task, 0) + 1

        if self.log_file:
            record = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "provider": "anthropic",
                "model": model,
                "task": task,
                "project": project,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "latency_ms": latency_ms,
                "estimated_cost_usd": round(cost, 6),
                "status": status,
            }
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.log_file, "a") as f:
                f.write(json.dumps(record) + "\n")

    def generate(
        self,
        prompt: str,
        system: str | None = None,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.3,
        budget_context: BudgetContext | None = None,
        task: str = "",
        project: str = "",
    ) -> AIResponse:
        """Generate a response from the AI model.

        Checks budget before calling, retries on transient errors,
        and logs usage after completion.
        """
        model = model or self.default_model

        # Pre-flight budget check
        status = self.check_budget(budget_context)
        if status == BudgetStatus.EXHAUSTED:
            raise BudgetExhaustedError(
                f"Budget exhausted for project {budget_context.project_id}"
            )
        if status == BudgetStatus.CRITICAL:
            logger.warning(
                "Budget critically low for project %s (%.1f%% used)",
                budget_context.project_id if budget_context else "unknown",
                budget_context.cost_usage_pct if budget_context else 0,
            )

        client = self._get_client()

        messages = [{"role": "user", "content": prompt}]
        kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": messages,
        }
        if system:
            kwargs["system"] = system
        if temperature is not None:
            kwargs["temperature"] = temperature

        last_error = None
        for attempt in range(self.max_retries + 1):
            start_time = time.time()
            try:
                response = client.messages.create(**kwargs)
                latency_ms = int((time.time() - start_time) * 1000)

                input_tokens = response.usage.input_tokens
                output_tokens = response.usage.output_tokens
                cost = estimate_cost(model, input_tokens, output_tokens)

                self._update_budget(budget_context, input_tokens, output_tokens, cost)
                self._log_call(model, task, project, input_tokens, output_tokens, cost, latency_ms, "success")

                text = ""
                for block in response.content:
                    if hasattr(block, "text"):
                        text += block.text

                return AIResponse(
                    text=text,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    estimated_cost_usd=cost,
                    model=model,
                    latency_ms=latency_ms,
                )

            except Exception as e:
                last_error = e
                latency_ms = int((time.time() - start_time) * 1000)
                error_str = str(e)

                # Don't retry auth errors or budget errors
                if "401" in error_str or isinstance(e, BudgetExhaustedError):
                    self._log_call(model, task, project, 0, 0, 0.0, latency_ms, f"error: {error_str}")
                    raise

                # Retry with exponential backoff
                if attempt < self.max_retries:
                    wait = 2 ** (attempt + 1)
                    logger.warning("AI call failed (attempt %d/%d), retrying in %ds: %s",
                                   attempt + 1, self.max_retries + 1, wait, error_str)
                    time.sleep(wait)
                else:
                    self._log_call(model, task, project, 0, 0, 0.0, latency_ms, f"error: {error_str}")

        raise last_error  # type: ignore[misc]

    def generate_structured(
        self,
        prompt: str,
        schema: dict,
        model: str | None = None,
        budget_context: BudgetContext | None = None,
        task: str = "",
        project: str = "",
    ) -> dict:
        """Generate a structured response matching the given JSON schema.

        Wraps the prompt to request JSON output and parses the result.
        """
        structured_prompt = (
            f"{prompt}\n\n"
            f"Respond with valid JSON matching this schema:\n"
            f"```json\n{json.dumps(schema, indent=2)}\n```\n"
            f"Output ONLY the JSON, no other text."
        )

        response = self.generate(
            prompt=structured_prompt,
            model=model,
            budget_context=budget_context,
            task=task,
            project=project,
        )

        # Parse JSON from response, handling markdown fences
        text = response.text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            # Remove first and last fence lines
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines)

        return json.loads(text)

    def get_usage(self) -> UsageReport:
        """Return cumulative usage statistics."""
        return self._usage
