#!/usr/bin/env python3
"""Data Journal CLI — command-line interface for the multi-agent research system."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from shared.utils.config import SystemConfig
from orchestrator.src.orchestrator import Orchestrator


def get_orchestrator(root_dir: str | None = None) -> Orchestrator:
    path = Path(root_dir) if root_dir else Path.cwd()
    config = SystemConfig.load(path)
    return Orchestrator(config=config)


def cmd_add(args):
    """Add a new research topic."""
    orch = get_orchestrator(args.root)

    questions = args.questions.split(";") if args.questions else []
    sources = []
    if args.sources:
        for s in args.sources.split(","):
            sources.append({"type": s.strip(), "queries": []})

    budget = {}
    if args.budget_tokens:
        budget["max_tokens"] = args.budget_tokens
    if args.budget_calls:
        budget["max_api_calls"] = args.budget_calls
    if args.budget_usd:
        budget["max_cost_usd"] = args.budget_usd

    tags = args.tags.split(",") if args.tags else []

    result = orch.add_topic(
        name=args.name,
        topic=args.topic,
        description=args.description or "",
        research_questions=questions,
        data_sources=sources or [{"type": "web_search", "queries": []}],
        priority=args.priority,
        budget=budget or None,
        tags=tags,
    )
    print(json.dumps(result, indent=2))


def cmd_list(args):
    """List projects."""
    orch = get_orchestrator(args.root)
    projects = orch.list_projects(args.status)

    if not projects:
        print("No projects found.")
        return

    print(f"{'Name':<30} {'Status':<12} {'Priority':<10} {'Created':<12}")
    print("-" * 64)
    for p in projects:
        print(f"{p['name']:<30} {p['status']:<12} {p['priority']:<10} {p.get('created', 'N/A'):<12}")


def cmd_status(args):
    """Get detailed project status."""
    orch = get_orchestrator(args.root)
    result = orch.get_status(args.name)
    print(json.dumps(result, indent=2))


def cmd_run(args):
    """Run the full research pipeline for a project."""
    orch = get_orchestrator(args.root)

    if args.phase:
        print(f"Running phase '{args.phase}' for project: {args.name}")
        result = orch.run_agent_phase(args.name, args.phase)
    else:
        print(f"Running full pipeline for project: {args.name}")
        result = orch.run_agent(args.name)

    print(json.dumps(result, indent=2, default=str))


def cmd_review(args):
    """Review a project's report."""
    orch = get_orchestrator(args.root)
    result = orch.review(args.name)
    print(json.dumps(result, indent=2))


def cmd_approve(args):
    """Approve a report and archive the project."""
    orch = get_orchestrator(args.root)
    result = orch.approve(args.name)
    print(json.dumps(result, indent=2))


def cmd_reject(args):
    """Reject a report with feedback."""
    orch = get_orchestrator(args.root)
    result = orch.reject(args.name, args.feedback)
    print(json.dumps(result, indent=2))


def cmd_budget(args):
    """View budget report."""
    orch = get_orchestrator(args.root)

    if args.name:
        result = orch.budget_manager.get_project_report(args.name)
    else:
        result = orch.get_budget_report()

    print(json.dumps(result, indent=2))


def cmd_pause(args):
    """Pause a project's agent."""
    orch = get_orchestrator(args.root)
    result = orch.pause(args.name)
    print(json.dumps(result, indent=2))


def cmd_resume(args):
    """Resume a paused agent."""
    orch = get_orchestrator(args.root)
    result = orch.resume(args.name)
    print(json.dumps(result, indent=2))


def main():
    parser = argparse.ArgumentParser(
        prog="data-journal",
        description="Data Journal — Multi-Agent Research System",
    )
    parser.add_argument("--root", type=str, default=None, help="Project root directory")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # add
    p_add = subparsers.add_parser("add", help="Add a new research topic")
    p_add.add_argument("name", help="Project name (kebab-case)")
    p_add.add_argument("topic", help="Research topic description")
    p_add.add_argument("--description", "-d", help="Detailed description")
    p_add.add_argument("--questions", "-q", help="Research questions (semicolon-separated)")
    p_add.add_argument("--sources", "-s", help="Data source types (comma-separated)")
    p_add.add_argument("--priority", "-p", default="normal", choices=["high", "normal", "low"])
    p_add.add_argument("--budget-tokens", type=int, help="Max token budget")
    p_add.add_argument("--budget-calls", type=int, help="Max API calls budget")
    p_add.add_argument("--budget-usd", type=float, help="Max USD budget")
    p_add.add_argument("--tags", "-t", help="Tags (comma-separated)")
    p_add.set_defaults(func=cmd_add)

    # list
    p_list = subparsers.add_parser("list", help="List projects")
    p_list.add_argument("--status", choices=["active", "created", "review", "revision", "archived"])
    p_list.set_defaults(func=cmd_list)

    # status
    p_status = subparsers.add_parser("status", help="Get project status")
    p_status.add_argument("name", help="Project name")
    p_status.set_defaults(func=cmd_status)

    # run
    p_run = subparsers.add_parser("run", help="Run research pipeline")
    p_run.add_argument("name", help="Project name")
    p_run.add_argument("--phase", choices=["initialize", "plan", "collect", "analyze", "draft", "submit"])
    p_run.set_defaults(func=cmd_run)

    # review
    p_review = subparsers.add_parser("review", help="Review project report")
    p_review.add_argument("name", help="Project name")
    p_review.set_defaults(func=cmd_review)

    # approve
    p_approve = subparsers.add_parser("approve", help="Approve and archive project")
    p_approve.add_argument("name", help="Project name")
    p_approve.set_defaults(func=cmd_approve)

    # reject
    p_reject = subparsers.add_parser("reject", help="Reject report with feedback")
    p_reject.add_argument("name", help="Project name")
    p_reject.add_argument("feedback", help="Review feedback")
    p_reject.set_defaults(func=cmd_reject)

    # budget
    p_budget = subparsers.add_parser("budget", help="View budget report")
    p_budget.add_argument("--name", help="Project name (omit for global report)")
    p_budget.set_defaults(func=cmd_budget)

    # pause
    p_pause = subparsers.add_parser("pause", help="Pause a project's agent")
    p_pause.add_argument("name", help="Project name")
    p_pause.set_defaults(func=cmd_pause)

    # resume
    p_resume = subparsers.add_parser("resume", help="Resume a paused agent")
    p_resume.add_argument("name", help="Project name")
    p_resume.set_defaults(func=cmd_resume)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    args.func(args)


if __name__ == "__main__":
    main()
