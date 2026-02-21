# Skill: Orchestration

## Purpose

Manage the lifecycle of research projects and coordinate agents. The orchestrator is the central control plane of the Data Journal system.

## Responsibilities

### Project Lifecycle Management
- Accept new topics and create project directories with initial configuration
- Transition projects between states: `active` → `review` → `archive`
- Handle re-activation when a reviewed report needs revision
- Archive completed projects with all artifacts preserved

### Agent Coordination
- Spawn one research agent per active project
- Assign tasks to agents based on project state and priority
- Monitor agent progress and health
- Enforce budget limits — pause or stop agents that exhaust their allocation
- Collect agent status reports and surface them to the user

### Scheduling
- Determine execution order when multiple projects are active
- Support priority levels: `high`, `normal`, `low`
- Budget-aware scheduling: prefer agents with remaining budget
- Round-robin fallback when priorities are equal

### State Persistence
- Save orchestrator state to disk on every significant event
- Support restart/resume without losing progress
- Maintain an event log of all orchestrator actions

## Interfaces

### Commands (CLI or programmatic)
- `add_topic(name, config)` — Create a new active project
- `list_projects(status_filter)` — List projects by status
- `get_status(project_name)` — Detailed status of a project
- `review(project_name)` — Enter review mode for a project
- `approve(project_name)` — Move project to archive
- `reject(project_name, feedback)` — Send project back to active with feedback
- `set_budget(project_name, budget)` — Update budget allocation
- `pause(project_name)` / `resume(project_name)` — Control agent execution

### Events Emitted
- `project.created`, `project.state_changed`, `project.archived`
- `agent.started`, `agent.paused`, `agent.completed`, `agent.budget_exhausted`
- `report.draft_ready`, `report.approved`, `report.revision_requested`

## Configuration

```yaml
orchestrator:
  max_concurrent_agents: 5
  default_budget:
    max_tokens: 1000000
    max_api_calls: 500
    max_cost_usd: 50.00
  scheduling:
    strategy: priority  # priority | round_robin | budget_aware
    tick_interval_seconds: 60
  persistence:
    state_file: orchestrator/state.json
    event_log: orchestrator/events.jsonl
```

## Dependencies
- `shared/ai_client/` for AI service calls
- `shared/models/` for project and agent data models
- `config/` for global settings
