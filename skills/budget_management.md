# Skill: Budget Management

## Purpose

Track, enforce, and report on resource usage across all agents and projects. Budgets ensure that research costs remain controlled while allowing agents autonomy within their allocation.

## Budget Dimensions

### Token Usage
- Track input tokens and output tokens separately
- Map to cost based on model pricing
- Support different rates for different models

### API Call Count
- Count each AI service call
- Useful for rate-limited subscription plans
- Track calls by type (generation, embedding, search)

### Dollar Cost
- Calculate estimated cost based on token usage and model pricing
- Support multiple currency display
- Include non-AI costs if applicable (API fees for data sources)

## Budget Hierarchy

```
Global Budget Pool
├── Project A Budget (allocated from pool)
│   └── Agent A (draws from Project A)
├── Project B Budget
│   └── Agent B (draws from Project B)
└── Unallocated Reserve
```

## Budget Lifecycle

### Allocation
- When a project is created, budget is allocated from the global pool
- Default budget comes from `orchestrator/config/`
- Can be overridden per-project in `project.yaml`
- Orchestrator validates that allocation doesn't exceed available pool

### Tracking
- Every AI call logs: timestamp, model, input_tokens, output_tokens, estimated_cost
- Running totals maintained in real-time
- Usage persisted to `projects/<topic>/logs/budget.jsonl`

### Enforcement
- Before each AI call, agent checks: `remaining_budget >= estimated_call_cost`
- Thresholds trigger actions:
  - **75% used**: Log warning
  - **90% used**: Notify orchestrator, agent enters conservative mode
  - **100% used**: Agent pauses, requests budget increase or wraps up

### Reporting
- Per-project budget usage summary
- Per-agent cost breakdown by task type
- Historical trend of spending across projects
- Cost-per-report metric for efficiency tracking

## AI Service Modes

### Subscription Mode (Claude Code)
- Budget tracked in tokens against subscription limits
- No direct dollar cost per call
- Daily/monthly token limits apply
- Agent must be aware of shared token pool with other uses

### API Mode (Direct API Calls)
- Budget tracked in tokens and dollar cost
- API key managed via environment variables
- Support for multiple API providers with different pricing:

```yaml
ai_services:
  claude:
    provider: anthropic
    model: claude-sonnet-4-20250514
    input_cost_per_1k: 0.003
    output_cost_per_1k: 0.015
  claude_haiku:
    provider: anthropic
    model: claude-haiku-4-20250414
    input_cost_per_1k: 0.00025
    output_cost_per_1k: 0.00125
```

## Budget Configuration

```yaml
budget:
  global_pool:
    max_tokens: 10000000
    max_cost_usd: 500.00
  default_project:
    max_tokens: 500000
    max_api_calls: 200
    max_cost_usd: 25.00
  alerts:
    warn_at_percent: 75
    critical_at_percent: 90
  tracking:
    log_file: budget.jsonl
    report_interval_minutes: 60
```

## Budget Log Format

```jsonl
{"timestamp": "2026-02-21T14:30:00Z", "project": "market-trends", "agent": "agent-001", "model": "claude-sonnet-4-20250514", "task": "draft_introduction", "input_tokens": 2500, "output_tokens": 1200, "estimated_cost_usd": 0.0255, "cumulative_tokens": 125000, "cumulative_cost_usd": 3.45, "budget_remaining_pct": 86.2}
```
