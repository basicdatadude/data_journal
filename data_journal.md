# Data Journal — Project Plan

## Vision

Build an AI-orchestrated research platform where autonomous agents investigate topics, collect data, perform rigorous analysis, and produce academic-quality whitepapers — all under human oversight with configurable budgets and iterative review cycles.

---

## Phase 1: Foundation

**Goal**: Establish the core infrastructure — project structure, configuration system, AI client abstraction, and basic orchestration.

### 1.1 Project Scaffold
- [x] Define directory structure
- [x] Create `claude.md` project context
- [x] Create `data_journal.md` project plan
- [x] Create skill documentation in `skills/`
- [x] Build all necessary directories with placeholder READMEs

### 1.2 Configuration System
- [ ] Define global config schema (`config/settings.yaml`)
- [ ] Define project config schema (`project.yaml` template)
- [ ] Implement config loader with validation
- [ ] Support environment variable overrides for secrets (API keys)

### 1.3 AI Client Abstraction
- [ ] Create `shared/ai_client/` module
- [ ] Implement Claude API client with token/cost tracking
- [ ] Implement subscription-mode client (for Claude Code sessions)
- [ ] Add budget enforcement: per-agent limits on tokens, calls, or cost
- [ ] Add fallback/routing logic for multiple AI service backends

### 1.4 Data Models
- [ ] Define `Project` model (topic, status, budget, agent config, metadata)
- [ ] Define `AgentState` model (current task, progress, token usage)
- [ ] Define `DataRecord` model (source, timestamp, content, metadata)
- [ ] Define `Report` model (title, status, version, sections, references)

---

## Phase 2: Data Pipeline

**Goal**: Build the crawling, ingestion, and storage layer that agents use to gather research data.

### 2.1 Crawler Framework
- [ ] Design pluggable crawler interface
- [ ] Implement web search crawler (using search APIs)
- [ ] Implement web page content extractor (HTML → structured text)
- [ ] Implement academic paper fetcher (arXiv, Semantic Scholar, etc.)
- [ ] Implement dataset fetcher (government data portals, public APIs)
- [ ] Add rate limiting and politeness policies
- [ ] Add provenance tracking (source URL, access date, content hash)

### 2.2 Data Ingestion
- [ ] Build ingestion pipeline: raw → cleaned → normalized
- [ ] Implement text extraction and cleaning
- [ ] Implement structured data parsing (CSV, JSON, tables)
- [ ] Add deduplication logic
- [ ] Add quality scoring for ingested data

### 2.3 Storage Layer
- [ ] Implement file-based storage for project data (`projects/<topic>/data/`)
- [ ] Add metadata index (SQLite or JSON-based) for fast querying
- [ ] Implement data versioning (track changes to collected datasets)
- [ ] Add export utilities (to CSV, JSON, Parquet)

---

## Phase 3: Analysis Engine

**Goal**: Provide tools for pattern detection, statistical analysis, and insight generation that agents can invoke.

### 3.1 Pattern Detection
- [ ] Implement trend detection (time-series analysis)
- [ ] Implement correlation finder (cross-variable relationships)
- [ ] Implement anomaly detection
- [ ] Implement text clustering and topic modeling
- [ ] Add AI-assisted pattern interpretation

### 3.2 Statistical Analysis
- [ ] Implement descriptive statistics module
- [ ] Implement hypothesis testing framework
- [ ] Implement regression analysis tools
- [ ] Add visualization generation (matplotlib/plotly charts)
- [ ] Add reproducibility tooling (seed tracking, environment capture)

### 3.3 Analysis Orchestration
- [ ] Define analysis plan schema (what analyses to run, in what order)
- [ ] Implement analysis runner that executes plans
- [ ] Add result caching and incremental re-analysis
- [ ] Generate analysis summaries for report integration

---

## Phase 4: Agent Framework

**Goal**: Build the autonomous agent that drives each research project through its lifecycle.

### 4.1 Base Agent
- [ ] Define agent interface: `initialize`, `plan`, `execute`, `report`, `reflect`
- [ ] Implement agent state machine (idle → researching → analyzing → drafting → reviewing)
- [ ] Add memory/context management (what the agent knows, what it has done)
- [ ] Add logging and audit trail per agent
- [ ] Implement budget-aware execution (check budget before each AI call)

### 4.2 Research Agent
- [ ] Implement research planning: given a topic, generate a research plan
- [ ] Implement iterative data collection: search → evaluate → collect → repeat
- [ ] Implement gap analysis: identify what data is still needed
- [ ] Implement source quality assessment
- [ ] Add checkpoint/resume capability

### 4.3 Agent Communication
- [ ] Define message protocol between agents and orchestrator
- [ ] Implement status reporting (progress, blockers, budget usage)
- [ ] Implement task assignment receipt and completion acknowledgment

---

## Phase 5: Report Generation

**Goal**: Produce polished, academic-quality whitepapers from collected data and analysis results.

### 5.1 Report Structure
- [ ] Define whitepaper template (abstract, introduction, methodology, results, discussion, conclusion, references)
- [ ] Create Markdown template with proper academic formatting
- [ ] Create LaTeX template for publication-ready output
- [ ] Define quality checklist (citations, methodology, statistical claims)

### 5.2 Report Composition
- [ ] Implement section-by-section drafting with AI assistance
- [ ] Implement citation management (collect, format, insert references)
- [ ] Implement figure/table integration from analysis outputs
- [ ] Add cross-reference and consistency checking
- [ ] Implement iterative revision based on review feedback

### 5.3 Quality Assurance
- [ ] Implement automated quality checks (citation completeness, logical flow, statistical validity)
- [ ] Implement plagiarism/originality scoring
- [ ] Add readability scoring
- [ ] Generate quality report alongside the whitepaper

---

## Phase 6: Orchestration Layer

**Goal**: Build the central coordinator that manages the full system — projects, agents, budgets, and lifecycle transitions.

### 6.1 Project Management
- [ ] Implement project CRUD (create, read, update, delete/archive)
- [ ] Implement topic list management (active vs. archive)
- [ ] Add project status dashboard (CLI or simple web view)
- [ ] Implement project state transitions with validation

### 6.2 Agent Lifecycle Management
- [ ] Implement agent spawning (one agent per active project)
- [ ] Implement agent scheduling (round-robin, priority-based, or budget-aware)
- [ ] Add agent health monitoring and restart logic
- [ ] Implement graceful shutdown and state persistence

### 6.3 Budget Management
- [ ] Implement global budget pool with per-agent allocation
- [ ] Track token usage, API call count, and estimated cost in real-time
- [ ] Add budget alerts and automatic throttling
- [ ] Generate budget usage reports

### 6.4 Human Review Interface
- [ ] Implement review queue (list projects awaiting review)
- [ ] Provide diff view for report revisions
- [ ] Accept approve/reject/revise-with-feedback actions
- [ ] Route feedback back to the agent for iteration

---

## Phase 7: Integration & Polish

**Goal**: End-to-end testing, documentation, and operational readiness.

### 7.1 Integration Testing
- [ ] End-to-end test: topic → crawl → analyze → report → review → archive
- [ ] Load testing with multiple concurrent agents
- [ ] Budget exhaustion scenarios
- [ ] Network failure and retry handling

### 7.2 Documentation
- [ ] User guide: how to add topics, configure budgets, review reports
- [ ] Developer guide: how to add new crawlers, analyses, or report templates
- [ ] API reference for all modules
- [ ] Deployment guide

### 7.3 Operational Tooling
- [ ] CLI for common operations (add topic, check status, review report)
- [ ] Logging aggregation and search
- [ ] Metrics collection (projects completed, average time-to-completion, budget efficiency)

---

## Current Status

**Phase**: 1.1 — Project Scaffold
**Active Projects**: None yet
**Next Step**: Complete Phase 1.2 (Configuration System) and Phase 1.3 (AI Client)

---

## Design Decisions Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-02-21 | Python 3.11+ as primary language | Mature ecosystem for data science, web crawling, and AI integration |
| 2026-02-21 | File-based project storage | Keeps projects self-contained and git-friendly; avoids database dependency for MVP |
| 2026-02-21 | YAML for configuration | Human-readable, supports complex nested config, widely used in Python ecosystem |
| 2026-02-21 | One agent per project | Simplifies state management; agents can be parallelized across projects |
| 2026-02-21 | Dual AI access mode (subscription + API) | Supports both interactive Claude Code sessions and automated batch processing |
