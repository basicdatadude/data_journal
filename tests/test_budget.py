"""Tests for budget management."""

import pytest
from shared.ai_client.client import BudgetContext, BudgetStatus, estimate_cost
from shared.ai_client.budget import BudgetManager, GlobalBudgetPool, BudgetAllocation


class TestBudgetContext:
    def test_healthy_budget(self):
        ctx = BudgetContext(project_id="test", max_tokens=100_000, max_cost_usd=10.0)
        assert ctx.status == BudgetStatus.HEALTHY
        assert ctx.remaining_tokens == 100_000

    def test_warning_threshold(self):
        ctx = BudgetContext(
            project_id="test",
            max_tokens=100_000,
            used_tokens=76_000,
            warn_at_percent=75,
        )
        assert ctx.status == BudgetStatus.WARNING

    def test_critical_threshold(self):
        ctx = BudgetContext(
            project_id="test",
            max_tokens=100_000,
            used_tokens=91_000,
            critical_at_percent=90,
        )
        assert ctx.status == BudgetStatus.CRITICAL

    def test_exhausted(self):
        ctx = BudgetContext(
            project_id="test",
            max_tokens=100_000,
            used_tokens=100_001,
        )
        assert ctx.status == BudgetStatus.EXHAUSTED

    def test_exhausted_by_calls(self):
        ctx = BudgetContext(
            project_id="test",
            max_api_calls=10,
            used_api_calls=10,
        )
        assert ctx.status == BudgetStatus.EXHAUSTED


class TestEstimateCost:
    def test_sonnet_pricing(self):
        cost = estimate_cost("claude-sonnet-4-20250514", 1000, 1000)
        assert cost > 0
        assert cost == pytest.approx(0.003 + 0.015, abs=0.001)

    def test_haiku_cheaper(self):
        sonnet_cost = estimate_cost("claude-sonnet-4-20250514", 1000, 1000)
        haiku_cost = estimate_cost("claude-haiku-4-20250414", 1000, 1000)
        assert haiku_cost < sonnet_cost


class TestGlobalBudgetPool:
    def test_allocate(self):
        pool = GlobalBudgetPool(max_tokens=1_000_000, max_cost_usd=100.0)
        pool.allocate("project-a", 500_000, 200, 50.0)
        assert pool.available_tokens == 500_000
        assert pool.available_cost == pytest.approx(50.0)

    def test_cannot_over_allocate(self):
        pool = GlobalBudgetPool(max_tokens=100_000, max_cost_usd=10.0)
        pool.allocate("a", 60_000, 100, 6.0)
        with pytest.raises(ValueError):
            pool.allocate("b", 60_000, 100, 6.0)

    def test_release(self):
        pool = GlobalBudgetPool(max_tokens=100_000, max_cost_usd=10.0)
        pool.allocate("a", 50_000, 100, 5.0)
        pool.release("a")
        assert pool.available_tokens == 100_000


class TestBudgetManager:
    def test_create_and_check(self, tmp_path):
        mgr = BudgetManager(tmp_path)
        ctx = mgr.create_context("test-project", max_tokens=100_000, max_cost_usd=10.0)
        assert ctx.project_id == "test-project"
        assert mgr.check_status("test-project") == BudgetStatus.HEALTHY

    def test_roundtrip(self, tmp_path):
        mgr = BudgetManager(tmp_path)
        mgr.create_context("test", max_tokens=50_000)
        mgr.save_state()

        mgr2 = BudgetManager(tmp_path)
        mgr2.load_state()
        ctx = mgr2.get_context("test")
        assert ctx is not None
        assert ctx.max_tokens == 50_000
