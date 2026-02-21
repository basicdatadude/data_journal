# Skill: Project Management

## Purpose

Manage the lifecycle of individual research projects from creation through archival. Each project is a self-contained unit with its own data, analysis, report, and configuration.

## Project States

```
CREATED → ACTIVE → REVIEW → ARCHIVED
              ↑        ↓
              └── REVISION
```

| State | Description |
|-------|-------------|
| `created` | Project directory initialized, config set, awaiting agent start |
| `active` | Agent is actively researching, collecting data, analyzing, or drafting |
| `review` | Report submitted for human review |
| `revision` | Feedback received, agent is revising (sub-state of active) |
| `archived` | Report approved, project complete, moved to `projects/archive/` |

## Project Configuration (`project.yaml`)

```yaml
project:
  name: "market-trends-2026"
  topic: "Global market trends in renewable energy investment"
  description: >
    Investigate trends in renewable energy investment globally,
    covering solar, wind, battery storage, and hydrogen.
    Focus on 2020-2026 period with emphasis on policy impacts.
  status: active
  priority: high
  created_date: "2026-02-21"

  research_questions:
    - "How has global renewable energy investment changed since 2020?"
    - "Which sectors show the strongest growth trajectory?"
    - "What policy changes have had the most significant impact?"
    - "How do regional investment patterns differ?"

  agent:
    model: claude-sonnet-4-20250514
    budget:
      max_tokens: 500000
      max_api_calls: 200
      max_cost_usd: 25.00

  data_sources:
    - type: web_search
      queries: ["renewable energy investment 2020-2026", "solar investment trends"]
    - type: academic
      queries: ["renewable energy policy impact investment"]
    - type: dataset
      sources: ["IEA", "IRENA", "Bloomberg NEF"]

  report:
    template: academic_whitepaper
    citation_format: apa
    target_length_words: 5000

  tags: [energy, investment, policy, global]
```

## Project Operations

### Create
1. Validate topic and configuration
2. Create project directory under `projects/active/`
3. Initialize subdirectories: `data/`, `analysis/`, `report/`, `references/`, `logs/`
4. Write `project.yaml`
5. Register with orchestrator

### Update
- Modify config fields (budget, priority, data sources)
- Add/remove research questions
- Update status

### Review
1. Agent marks report as ready for review
2. Project state → `review`
3. Human reads report, runs quality checks
4. Human approves → archive, or provides feedback → revision

### Archive
1. Move project directory from `projects/active/` to `projects/archive/`
2. Update project status in config
3. Generate final summary (topic, dates, budget used, report quality score)
4. Decommission agent

### Re-activate
- An archived project can be re-activated if new data or questions emerge
- Copy from archive back to active, reset agent state

## Topic List Management

The master topic list is maintained in `config/topics.yaml`:

```yaml
topics:
  active:
    - name: "market-trends-2026"
      priority: high
      created: "2026-02-21"
    - name: "ai-regulation-landscape"
      priority: normal
      created: "2026-02-20"

  archive:
    - name: "supply-chain-disruptions-2025"
      completed: "2026-01-15"
      report: "projects/archive/supply-chain-disruptions-2025/report/final/whitepaper.pdf"
```

## Project Directory Template

When a new project is created, this structure is generated:

```
projects/active/<project-name>/
├── project.yaml
├── data/
│   ├── raw/
│   └── processed/
├── analysis/
│   ├── notebooks/
│   ├── scripts/
│   └── outputs/
├── report/
│   ├── drafts/
│   └── final/
├── references/
│   └── bibliography.yaml
└── logs/
    ├── agent.log
    └── budget.jsonl
```
