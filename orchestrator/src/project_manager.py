"""Project management: create, update, transition, and archive projects."""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from shared.models.project import (
    Project,
    ProjectConfig,
    ProjectStatus,
    Priority,
    BudgetConfig,
    AgentConfig,
    DataSourceConfig,
    ReportConfig,
)
from shared.models.events import Event, EventType
from shared.utils.files import (
    create_project_dirs,
    load_yaml,
    save_yaml,
    move_project,
)
from shared.utils.logging import get_logger

logger = get_logger("project_manager")


class ProjectManager:
    """Manage the lifecycle of research projects."""

    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.active_dir = root_dir / "projects" / "active"
        self.archive_dir = root_dir / "projects" / "archive"
        self.topics_file = root_dir / "config" / "topics.yaml"
        self.template_file = root_dir / "config" / "project_template.yaml"

    def create_project(
        self,
        name: str,
        topic: str,
        description: str = "",
        research_questions: list[str] | None = None,
        data_sources: list[dict] | None = None,
        priority: str = "normal",
        budget: dict | None = None,
        tags: list[str] | None = None,
    ) -> Project:
        """Create a new research project with its directory structure."""
        project_path = self.active_dir / name
        if project_path.exists():
            raise ValueError(f"Project '{name}' already exists")

        # Build config
        budget_config = BudgetConfig(**(budget or {}))
        agent_config = AgentConfig(budget=budget_config)

        sources = []
        for ds in (data_sources or []):
            sources.append(DataSourceConfig(
                source_type=ds.get("type", "web_search"),
                queries=ds.get("queries", []),
            ))

        config = ProjectConfig(
            name=name,
            topic=topic,
            description=description,
            status=ProjectStatus.CREATED,
            priority=priority,
            research_questions=research_questions or [],
            agent=agent_config,
            data_sources=sources,
            tags=tags or [],
        )

        # Create directory structure
        create_project_dirs(project_path)

        # Save project config
        save_yaml(project_path / "project.yaml", config.to_dict())

        # Update topics registry
        self._add_to_topics(name, priority)

        project = Project(config=config, path=project_path)
        logger.info("Created project: %s", name)
        return project

    def load_project(self, name: str, status: str = "active") -> Project:
        """Load a project from disk."""
        if status == "active":
            project_path = self.active_dir / name
        else:
            project_path = self.archive_dir / name

        config_path = project_path / "project.yaml"
        if not config_path.exists():
            raise FileNotFoundError(f"Project '{name}' not found at {config_path}")

        data = load_yaml(config_path)
        config = ProjectConfig.from_dict(data)
        return Project(config=config, path=project_path)

    def list_projects(self, status_filter: str | None = None) -> list[dict]:
        """List projects, optionally filtered by status."""
        projects = []

        # Active projects
        if status_filter in (None, "active", "created", "review", "revision"):
            if self.active_dir.exists():
                for d in sorted(self.active_dir.iterdir()):
                    if d.is_dir() and (d / "project.yaml").exists():
                        config = ProjectConfig.from_dict(load_yaml(d / "project.yaml"))
                        if status_filter is None or config.status.value == status_filter:
                            projects.append({
                                "name": config.name,
                                "topic": config.topic,
                                "status": config.status.value,
                                "priority": config.priority.value,
                                "created": config.created_date,
                            })

        # Archived projects
        if status_filter in (None, "archived"):
            if self.archive_dir.exists():
                for d in sorted(self.archive_dir.iterdir()):
                    if d.is_dir() and (d / "project.yaml").exists():
                        config = ProjectConfig.from_dict(load_yaml(d / "project.yaml"))
                        projects.append({
                            "name": config.name,
                            "topic": config.topic,
                            "status": "archived",
                            "priority": config.priority.value,
                            "created": config.created_date,
                            "completed": config.completed_date,
                        })

        return projects

    def update_status(self, name: str, new_status: ProjectStatus) -> Project:
        """Transition a project to a new status."""
        project = self.load_project(name)
        old_status = project.status

        # Validate transition
        valid_transitions = {
            ProjectStatus.CREATED: {ProjectStatus.ACTIVE},
            ProjectStatus.ACTIVE: {ProjectStatus.REVIEW},
            ProjectStatus.REVIEW: {ProjectStatus.ARCHIVED, ProjectStatus.REVISION},
            ProjectStatus.REVISION: {ProjectStatus.REVIEW, ProjectStatus.ACTIVE},
        }

        allowed = valid_transitions.get(old_status, set())
        if new_status not in allowed:
            raise ValueError(
                f"Invalid transition: {old_status.value} → {new_status.value}. "
                f"Allowed: {', '.join(s.value for s in allowed)}"
            )

        project.status = new_status
        save_yaml(project.path / "project.yaml", project.config.to_dict())
        logger.info("Project %s: %s → %s", name, old_status.value, new_status.value)
        return project

    def archive_project(self, name: str) -> Path:
        """Move a project from active to archive."""
        project = self.load_project(name)
        project.config.status = ProjectStatus.ARCHIVED
        project.config.completed_date = datetime.now().isoformat()[:10]

        # Save updated config before moving
        save_yaml(project.path / "project.yaml", project.config.to_dict())

        # Move to archive
        archive_path = self.archive_dir / name
        move_project(project.path, archive_path)

        # Update topics registry
        self._move_to_archive(name)

        logger.info("Archived project: %s", name)
        return archive_path

    def reactivate_project(self, name: str) -> Project:
        """Move a project from archive back to active."""
        archive_path = self.archive_dir / name
        if not archive_path.exists():
            raise FileNotFoundError(f"Archived project '{name}' not found")

        active_path = self.active_dir / name
        move_project(archive_path, active_path)

        # Update config
        data = load_yaml(active_path / "project.yaml")
        config = ProjectConfig.from_dict(data)
        config.status = ProjectStatus.ACTIVE
        config.completed_date = ""
        save_yaml(active_path / "project.yaml", config.to_dict())

        # Update topics
        self._add_to_topics(name, config.priority.value)

        project = Project(config=config, path=active_path)
        logger.info("Reactivated project: %s", name)
        return project

    def update_config(self, name: str, updates: dict) -> Project:
        """Update specific fields in a project's configuration."""
        project = self.load_project(name)
        config_path = project.path / "project.yaml"
        data = load_yaml(config_path)

        proj = data.get("project", data)
        for key, value in updates.items():
            if key in proj:
                proj[key] = value
            elif "." in key:
                parts = key.split(".")
                target = proj
                for part in parts[:-1]:
                    target = target.setdefault(part, {})
                target[parts[-1]] = value

        save_yaml(config_path, data)
        return self.load_project(name)

    def get_project_summary(self, name: str) -> dict:
        """Get a summary of a project including data and analysis status."""
        project = self.load_project(name)
        raw_count = len(list(project.data_raw_dir.glob("*.json"))) if project.data_raw_dir.exists() else 0
        processed_exists = (project.data_processed_dir / "dataset.json").exists()
        draft_count = len(list((project.report_dir / "drafts").iterdir())) if (project.report_dir / "drafts").exists() else 0
        final_exists = (project.report_dir / "final" / "whitepaper.md").exists()

        return {
            "name": name,
            "topic": project.config.topic,
            "status": project.status.value,
            "priority": project.config.priority.value,
            "created": project.config.created_date,
            "research_questions": len(project.config.research_questions),
            "data": {
                "raw_sources": raw_count,
                "processed": processed_exists,
            },
            "report": {
                "drafts": draft_count,
                "final": final_exists,
            },
        }

    def _add_to_topics(self, name: str, priority: str):
        """Add a project to the topics registry."""
        topics = load_yaml(self.topics_file) or {"topics": {"active": [], "archive": []}}
        active = topics.get("topics", {}).get("active", []) or []

        # Don't duplicate
        if any(t.get("name") == name for t in active):
            return

        active.append({
            "name": name,
            "priority": priority,
            "created": datetime.now().isoformat()[:10],
        })
        topics.setdefault("topics", {})["active"] = active
        save_yaml(self.topics_file, topics)

    def _move_to_archive(self, name: str):
        """Move a project from active to archive in the topics registry."""
        topics = load_yaml(self.topics_file) or {"topics": {"active": [], "archive": []}}
        active = topics.get("topics", {}).get("active", []) or []
        archive = topics.get("topics", {}).get("archive", []) or []

        active = [t for t in active if t.get("name") != name]
        archive.append({
            "name": name,
            "completed": datetime.now().isoformat()[:10],
        })

        topics["topics"]["active"] = active
        topics["topics"]["archive"] = archive
        save_yaml(self.topics_file, topics)
