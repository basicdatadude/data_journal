"""File system utilities for project management."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import yaml


PROJECT_SUBDIRS = [
    "data/raw",
    "data/processed",
    "analysis/notebooks",
    "analysis/scripts",
    "analysis/outputs",
    "report/drafts",
    "report/final",
    "report/assets/figures",
    "report/assets/tables",
    "references",
    "logs",
]


def create_project_dirs(project_path: Path):
    """Create the standard project directory structure."""
    project_path.mkdir(parents=True, exist_ok=True)
    for subdir in PROJECT_SUBDIRS:
        (project_path / subdir).mkdir(parents=True, exist_ok=True)
    # Initialize empty bibliography
    bib_path = project_path / "references" / "bibliography.yaml"
    if not bib_path.exists():
        save_yaml(bib_path, {"references": []})


def move_project(src: Path, dst: Path):
    """Move a project directory from src to dst."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))


def load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


def save_yaml(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path) as f:
        return json.load(f)


def save_json(path: Path, data: Any):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def append_jsonl(path: Path, record: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(record) + "\n")


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    records = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def safe_write(path: Path, content: str):
    """Write content to a file, creating parent dirs as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        f.write(content)
