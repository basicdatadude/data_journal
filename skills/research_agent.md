# Skill: Research Agent

## Purpose

Autonomously investigate a given topic by planning research, collecting data, running analyses, and drafting reports. Each active project has one dedicated research agent.

## Agent Lifecycle

```
INITIALIZE → PLAN → COLLECT → ANALYZE → DRAFT → SUBMIT → [REVISE] → DONE
```

### States

1. **Initialize**: Load project config, review any existing data/progress, set up working context.
2. **Plan**: Generate a research plan — what questions to answer, what data to collect, what analyses to run.
3. **Collect**: Execute the data collection plan using the pipeline crawlers.
4. **Analyze**: Run analyses on collected data, detect patterns, generate insights.
5. **Draft**: Compose the whitepaper using analysis results and collected evidence.
6. **Submit**: Present the draft for human review.
7. **Revise**: Incorporate feedback and iterate (returns to Collect, Analyze, or Draft as needed).
8. **Done**: Report approved, agent is decommissioned.

## Responsibilities

### Research Planning
- Given a topic, decompose it into specific research questions
- Identify the types of data needed (quantitative, qualitative, historical, real-time)
- Determine which crawlers and data sources to use
- Estimate data collection scope and budget requirements
- Create a prioritized task list

### Data Collection
- Invoke crawlers from `pipeline/crawlers/` to gather data
- Evaluate source quality and relevance
- Perform gap analysis: identify what data is missing
- Iterate collection until sufficient coverage is achieved
- Maintain provenance records for all collected data

### Analysis Execution
- Select appropriate analysis methods from `analysis/`
- Execute analyses and capture results
- Interpret findings using AI assistance
- Generate visualizations and summary statistics
- Identify key insights for the report

### Report Drafting
- Follow the whitepaper template from `reports/templates/`
- Write each section with proper academic tone and structure
- Integrate figures, tables, and citations
- Run quality checks before submission
- Support iterative revision based on feedback

## Budget Awareness

The agent checks its remaining budget before every AI call:
- If budget is sufficient: proceed
- If budget is low (< 10% remaining): notify orchestrator, prioritize completing current task
- If budget is exhausted: stop execution, save state, report to orchestrator

## Memory & Context

The agent maintains a working memory:
- **Research plan**: The current plan and its completion status
- **Findings log**: Key facts, data points, and insights discovered
- **Decision log**: Why certain sources/methods were chosen or rejected
- **Iteration history**: What changed between drafts and why

## Configuration (per-project)

```yaml
agent:
  model: claude-sonnet-4-20250514  # or other supported model
  temperature: 0.3
  max_tokens_per_call: 4096
  budget:
    max_tokens: 500000
    max_api_calls: 200
    max_cost_usd: 25.00
  collection:
    max_sources: 50
    min_sources: 10
    quality_threshold: 0.7
  analysis:
    methods: [descriptive_stats, trend_detection, correlation, topic_modeling]
  report:
    template: academic_whitepaper
    citation_format: apa
    min_sections: 6
```

## Error Handling

- Network failures during crawling: retry with exponential backoff, skip after 3 failures
- AI API errors: retry once, then pause and notify orchestrator
- Analysis failures: log error, attempt alternative method, report if no methods succeed
- All errors are logged to `projects/<topic>/logs/agent.log`
