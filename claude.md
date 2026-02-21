# Data Journal — Multi-Agent Research System

## Project Overview

Data Journal is an AI-orchestrated research platform that crawls, collects, analyzes, and publishes academic-quality whitepapers on configurable topics. Each research topic is managed by a dedicated AI agent operating within a defined budget. Projects flow through a lifecycle: **active** (researching, analyzing, drafting) → **review** (human approval) → **archive** (completed).

## Architecture

### Core Components

1. **Orchestrator** (`orchestrator/`) — Central coordination layer that manages agent lifecycle, budget tracking, task scheduling, and project state transitions.
2. **Agents** (`agents/`) — Per-project research agents responsible for data collection, analysis, and report generation.
3. **Data Pipeline** (`pipeline/`) — Crawling, ingestion, cleaning, and storage of research data.
4. **Analysis Engine** (`analysis/`) — Pattern detection, statistical analysis, and insight generation.
5. **Report Generator** (`reports/`) — Whitepaper composition, formatting, citation management, and quality assurance.
6. **Projects** (`projects/`) — Each topic gets a self-contained directory with its data, code, analysis artifacts, and final report.

### Directory Structure

```
data_journal/
├── claude.md                  # This file — project context for Claude
├── data_journal.md            # Project plan and roadmap
├── skills/                    # Skill documentation files
├── orchestrator/              # AI orchestration layer
│   ├── config/                # System and agent configuration
│   ├── src/                   # Orchestrator source code
│   └── tests/                 # Orchestrator tests
├── agents/                    # Agent framework and definitions
│   ├── base/                  # Base agent class and shared utilities
│   ├── research/              # Research agent implementation
│   └── tests/                 # Agent tests
├── pipeline/                  # Data pipeline
│   ├── crawlers/              # Web crawlers and data fetchers
│   ├── ingest/                # Data ingestion and normalization
│   ├── storage/               # Data storage layer
│   └── tests/                 # Pipeline tests
├── analysis/                  # Analysis engine
│   ├── patterns/              # Pattern detection modules
│   ├── statistics/            # Statistical analysis tools
│   └── tests/                 # Analysis tests
├── reports/                   # Report generation
│   ├── templates/             # Whitepaper templates (LaTeX/Markdown)
│   ├── citations/             # Citation management
│   ├── generator/             # Report composition engine
│   └── tests/                 # Report tests
├── projects/                  # Individual research projects
│   ├── active/                # Currently active projects
│   └── archive/               # Completed projects
├── shared/                    # Shared utilities and libraries
│   ├── models/                # Data models and schemas
│   ├── utils/                 # Common utilities
│   └── ai_client/             # AI service client (Claude API / subscription)
├── config/                    # Global configuration
└── tests/                     # Integration and end-to-end tests
```

### Project Lifecycle

```
[Topic Added] → ACTIVE → [Crawl & Collect] → [Analyze] → [Draft Report]
                  ↑                                            ↓
                  └──── [Revisions Needed] ←── REVIEW ←── [Submit for Review]
                                                   ↓
                                               ARCHIVE
```

1. **Active**: Agent crawls historical and recent data, detects patterns, runs analyses, iterates on findings.
2. **Review**: Report submitted for human review. Owner confirms completion or requests continued iteration.
3. **Archive**: Approved reports and all project artifacts are preserved in the archive.

### Project Directory Structure (per topic)

Each project under `projects/active/<topic>/` or `projects/archive/<topic>/` contains:

```
<topic>/
├── project.yaml              # Project config: topic, budget, status, agent settings
├── data/                     # Raw and processed data
│   ├── raw/                  # Original crawled data
│   └── processed/            # Cleaned and normalized data
├── analysis/                 # Analysis code and outputs
│   ├── notebooks/            # Jupyter notebooks
│   ├── scripts/              # Analysis scripts
│   └── outputs/              # Analysis results, charts, tables
├── report/                   # Report drafts and final version
│   ├── drafts/               # Iterative drafts
│   └── final/                # Approved final whitepaper
├── references/               # Bibliography and source materials
└── logs/                     # Agent activity logs and audit trail
```

## AI Service Configuration

The system supports two modes of AI access:

1. **Claude Subscription** — Uses the Claude subscription token limit (for interactive sessions via Claude Code).
2. **API Mode** — Direct API calls to Claude or other AI services (for automated agent operations).

Budget is tracked per-agent with configurable limits in tokens, API calls, or dollar cost.

## Key Conventions

- **Language**: Python 3.11+
- **Package Manager**: pip with requirements.txt (or Poetry if preferred)
- **Config Format**: YAML for project configs, environment variables for secrets
- **Data Formats**: JSON, CSV, Parquet for data; Markdown and LaTeX for reports
- **Testing**: pytest for all test suites
- **Logging**: Structured JSON logging with per-agent log files
- **Version Control**: Each project's data and artifacts are tracked; large data files use .gitignore with documented retrieval steps

## Quality Standards for Reports

Reports must meet academic whitepaper standards:
- Clear thesis and structured argumentation
- Properly cited sources (APA or IEEE format)
- Statistical rigor with reproducible methodology
- Peer-review-ready language and formatting
- All supporting data and analysis code packaged with the report

## Working with This Codebase

- Read `data_journal.md` for the full project plan and current status
- Check `skills/` for detailed documentation on each system capability
- Active projects are in `projects/active/` — each is self-contained
- The orchestrator manages all agent coordination — start there for system-level changes
- All configuration lives in `config/` (global) and `orchestrator/config/` (orchestration-specific)
- Budget and token tracking is handled by `shared/ai_client/`
