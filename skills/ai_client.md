# Skill: AI Client

## Purpose

Provide a unified interface for AI service calls across the system, supporting both Claude subscription tokens and direct API access to Claude or other AI services. The AI client handles authentication, budget tracking, model routing, and error handling.

## Supported Modes

### 1. Claude Subscription Mode
- Used during interactive Claude Code sessions
- Token usage counted against subscription limits
- No API key required (uses session authentication)
- Best for: human-in-the-loop development, ad-hoc research, report review

### 2. Claude API Mode
- Direct calls to Anthropic's API
- Requires `ANTHROPIC_API_KEY` environment variable
- Token and cost tracking per call
- Supports all Claude models (Opus, Sonnet, Haiku)
- Best for: automated agent operations, batch processing

### 3. External AI Service Mode
- Support for other AI APIs as fallback or alternative
- Provider-agnostic interface
- Requires provider-specific API keys
- Best for: cost optimization, capability-specific routing

## Client Interface

```python
class AIClient:
    def generate(
        self,
        prompt: str,
        system: str = None,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 4096,
        temperature: float = 0.3,
        budget_context: BudgetContext = None,
    ) -> AIResponse

    def generate_structured(
        self,
        prompt: str,
        schema: dict,
        model: str = "claude-sonnet-4-20250514",
        budget_context: BudgetContext = None,
    ) -> dict

    def get_usage(self) -> UsageReport
    def check_budget(self, budget_context: BudgetContext) -> BudgetStatus
```

## Model Routing

The client can route requests to different models based on task type:

```yaml
model_routing:
  planning: claude-sonnet-4-20250514        # Research planning, analysis design
  drafting: claude-sonnet-4-20250514        # Report writing, section drafting
  analysis: claude-haiku-4-20250414         # Data interpretation, quick summaries
  quality_check: claude-sonnet-4-20250514   # Quality assurance, review
  extraction: claude-haiku-4-20250414       # Data extraction, parsing
```

This allows cost optimization — use cheaper/faster models for simpler tasks.

## Budget Integration

Every AI call passes through budget checking:

```python
# Before call
status = client.check_budget(budget_context)
if status == BudgetStatus.EXHAUSTED:
    raise BudgetExhaustedError()
if status == BudgetStatus.CRITICAL:
    logger.warning("Budget critically low, entering conservative mode")

# Make call
response = client.generate(prompt, budget_context=budget_context)

# After call — usage automatically logged
# response.usage: {input_tokens, output_tokens, estimated_cost}
```

## Error Handling

| Error | Handling |
|-------|----------|
| Rate limit (429) | Exponential backoff: 2s, 4s, 8s, 16s |
| Server error (500/503) | Retry up to 3 times with backoff |
| Authentication error (401) | Fail immediately, log error, notify orchestrator |
| Budget exhausted | Fail immediately, save agent state |
| Network timeout | Retry once, then fail and log |
| Invalid response | Retry once with same prompt, then log and skip |

## Configuration

```yaml
ai_client:
  default_provider: anthropic
  default_model: claude-sonnet-4-20250514

  anthropic:
    api_key_env: ANTHROPIC_API_KEY
    base_url: https://api.anthropic.com
    max_retries: 3
    timeout_seconds: 120

  subscription:
    enabled: true
    daily_token_limit: 500000

  logging:
    log_prompts: false        # Privacy: don't log full prompts by default
    log_usage: true           # Always log token counts and costs
    log_file: ai_client.jsonl
```

## Usage Logging

Every call is logged (with configurable detail level):

```jsonl
{"timestamp": "2026-02-21T14:30:00Z", "provider": "anthropic", "model": "claude-sonnet-4-20250514", "task": "draft_methodology", "project": "market-trends", "input_tokens": 3200, "output_tokens": 1800, "latency_ms": 4500, "estimated_cost_usd": 0.0366, "status": "success"}
```
