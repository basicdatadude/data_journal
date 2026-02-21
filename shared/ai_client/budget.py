"""Budget management — tracking, enforcement, and reporting."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from shared.ai_client.client import BudgetContext, BudgetStatus, estimate_cost
from shared.utils.files import append_jsonl, read_jsonl, save_json, load_json
from shared.utils.logging import get_logger

logger = get_logger("budget")


@dataclass
class BudgetAllocation:
    """A single project's budget allocation from the global pool."""
    project_id: str
    max_tokens: int
    max_api_calls: int
    max_cost_usd: float
    allocated_at: str = ""

    def __post_init__(self):
        if not self.allocated_at:
            self.allocated_at = datetime.utcnow().isoformat() + "Z"


@dataclass
class GlobalBudgetPool:
    """Manages the global budget pool and per-project allocations."""

    max_tokens: int = 10_000_000
    max_cost_usd: float = 500.00
    allocations: dict[str, BudgetAllocation] = field(default_factory=dict)

    @property
    def allocated_tokens(self) -> int:
        return sum(a.max_tokens for a in self.allocations.values())

    @property
    def allocated_cost(self) -> float:
        return sum(a.max_cost_usd for a in self.allocations.values())

    @property
    def available_tokens(self) -> int:
        return max(0, self.max_tokens - self.allocated_tokens)

    @property
    def available_cost(self) -> float:
        return max(0.0, self.max_cost_usd - self.allocated_cost)

    def can_allocate(self, tokens: int, cost: float) -> bool:
        return tokens <= self.available_tokens and cost <= self.available_cost

    def allocate(self, project_id: str, tokens: int, api_calls: int, cost: float) -> BudgetAllocation:
        if not self.can_allocate(tokens, cost):
            raise ValueError(
                f"Cannot allocate {tokens} tokens / ${cost:.2f} — "
                f"available: {self.available_tokens} tokens / ${self.available_cost:.2f}"
            )
        alloc = BudgetAllocation(
            project_id=project_id,
            max_tokens=tokens,
            max_api_calls=api_calls,
            max_cost_usd=cost,
        )
        self.allocations[project_id] = alloc
        logger.info("Allocated budget for %s: %d tokens, %d calls, $%.2f",
                     project_id, tokens, api_calls, cost)
        return alloc

    def release(self, project_id: str):
        if project_id in self.allocations:
            del self.allocations[project_id]
            logger.info("Released budget for %s", project_id)

    def to_dict(self) -> dict:
        return {
            "max_tokens": self.max_tokens,
            "max_cost_usd": self.max_cost_usd,
            "allocations": {
                pid: {
                    "project_id": a.project_id,
                    "max_tokens": a.max_tokens,
                    "max_api_calls": a.max_api_calls,
                    "max_cost_usd": a.max_cost_usd,
                    "allocated_at": a.allocated_at,
                }
                for pid, a in self.allocations.items()
            },
            "allocated_tokens": self.allocated_tokens,
            "available_tokens": self.available_tokens,
            "allocated_cost_usd": round(self.allocated_cost, 2),
            "available_cost_usd": round(self.available_cost, 2),
        }

    @classmethod
    def from_dict(cls, data: dict) -> GlobalBudgetPool:
        pool = cls(
            max_tokens=data.get("max_tokens", 10_000_000),
            max_cost_usd=data.get("max_cost_usd", 500.00),
        )
        for pid, adict in data.get("allocations", {}).items():
            pool.allocations[pid] = BudgetAllocation(
                project_id=adict["project_id"],
                max_tokens=adict["max_tokens"],
                max_api_calls=adict["max_api_calls"],
                max_cost_usd=adict["max_cost_usd"],
                allocated_at=adict.get("allocated_at", ""),
            )
        return pool


class BudgetManager:
    """Manages budget tracking, enforcement, and reporting across all projects."""

    def __init__(self, root_dir: Path, global_pool: GlobalBudgetPool | None = None):
        self.root_dir = root_dir
        self.state_file = root_dir / "orchestrator" / "budget_state.json"
        self.pool = global_pool or GlobalBudgetPool()
        self._contexts: dict[str, BudgetContext] = {}

    def save_state(self):
        """Persist budget state to disk."""
        state = {
            "pool": self.pool.to_dict(),
            "contexts": {pid: ctx.to_dict() for pid, ctx in self._contexts.items()},
        }
        save_json(self.state_file, state)

    def load_state(self):
        """Load budget state from disk."""
        state = load_json(self.state_file)
        if not state:
            return
        self.pool = GlobalBudgetPool.from_dict(state.get("pool", {}))
        for pid, ctx_data in state.get("contexts", {}).items():
            self._contexts[pid] = BudgetContext.from_dict(ctx_data)

    def create_context(
        self,
        project_id: str,
        max_tokens: int = 500_000,
        max_api_calls: int = 200,
        max_cost_usd: float = 25.00,
    ) -> BudgetContext:
        """Create a budget context for a project, allocating from the global pool."""
        self.pool.allocate(project_id, max_tokens, max_api_calls, max_cost_usd)
        ctx = BudgetContext(
            project_id=project_id,
            max_tokens=max_tokens,
            max_api_calls=max_api_calls,
            max_cost_usd=max_cost_usd,
        )
        self._contexts[project_id] = ctx
        self.save_state()
        return ctx

    def get_context(self, project_id: str) -> BudgetContext | None:
        return self._contexts.get(project_id)

    def release_context(self, project_id: str):
        """Release a project's budget back to the pool."""
        self.pool.release(project_id)
        self._contexts.pop(project_id, None)
        self.save_state()

    def check_status(self, project_id: str) -> BudgetStatus:
        ctx = self._contexts.get(project_id)
        if ctx is None:
            return BudgetStatus.HEALTHY
        return ctx.status

    def record_usage(
        self,
        project_id: str,
        model: str,
        task: str,
        input_tokens: int,
        output_tokens: int,
    ):
        """Record token usage for a project and write to budget log."""
        ctx = self._contexts.get(project_id)
        cost = estimate_cost(model, input_tokens, output_tokens)
        if ctx:
            ctx.used_tokens += input_tokens + output_tokens
            ctx.used_api_calls += 1
            ctx.used_cost_usd += cost

        # Write to project budget log
        log_path = self.root_dir / "projects" / "active" / project_id / "logs" / "budget.jsonl"
        record = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "project": project_id,
            "model": model,
            "task": task,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "estimated_cost_usd": round(cost, 6),
            "cumulative_tokens": ctx.used_tokens if ctx else 0,
            "cumulative_cost_usd": round(ctx.used_cost_usd, 6) if ctx else 0,
            "budget_remaining_pct": round(100 - ctx.token_usage_pct, 1) if ctx else 100,
        }
        append_jsonl(log_path, record)
        self.save_state()

    def get_project_report(self, project_id: str) -> dict:
        """Generate a budget usage report for a project."""
        ctx = self._contexts.get(project_id)
        if ctx is None:
            return {"project_id": project_id, "status": "no_budget_allocated"}
        return {
            "project_id": project_id,
            "budget": ctx.to_dict(),
            "pool_summary": {
                "available_tokens": self.pool.available_tokens,
                "available_cost_usd": round(self.pool.available_cost, 2),
            },
        }

    def get_global_report(self) -> dict:
        """Generate a global budget report across all projects."""
        return {
            "pool": self.pool.to_dict(),
            "projects": {pid: ctx.to_dict() for pid, ctx in self._contexts.items()},
            "total_used_tokens": sum(c.used_tokens for c in self._contexts.values()),
            "total_used_cost_usd": round(
                sum(c.used_cost_usd for c in self._contexts.values()), 4
            ),
        }
