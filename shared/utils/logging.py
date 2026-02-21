"""Structured JSON logging for the Data Journal system."""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime
from pathlib import Path


class JSONFormatter(logging.Formatter):
    """Format log records as JSON lines."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "project"):
            log_entry["project"] = record.project
        if hasattr(record, "agent_id"):
            log_entry["agent_id"] = record.agent_id
        if record.exc_info and record.exc_info[1]:
            log_entry["exception"] = str(record.exc_info[1])
        for key in ("data", "event_type", "task"):
            if hasattr(record, key):
                log_entry[key] = getattr(record, key)
        return json.dumps(log_entry)


def get_logger(
    name: str,
    level: str = "INFO",
    log_file: Path | None = None,
    json_format: bool = True,
) -> logging.Logger:
    """Create a configured logger.

    Args:
        name: Logger name (typically module or component name).
        level: Log level string.
        log_file: Optional file path for log output.
        json_format: Use JSON formatting (True) or plain text (False).
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    if logger.handlers:
        return logger

    formatter: logging.Formatter
    if json_format:
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        )

    console = logging.StreamHandler(sys.stderr)
    console.setFormatter(formatter)
    logger.addHandler(console)

    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


class ProjectLogger:
    """Logger scoped to a specific project, writing to the project's log directory."""

    def __init__(self, project_name: str, logs_dir: Path, level: str = "INFO"):
        self.project_name = project_name
        self.logs_dir = logs_dir
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self._logger = get_logger(
            f"project.{project_name}",
            level=level,
            log_file=logs_dir / "agent.log",
        )

    def info(self, message: str, **extra):
        self._logger.info(message, extra={"project": self.project_name, **extra})

    def warning(self, message: str, **extra):
        self._logger.warning(message, extra={"project": self.project_name, **extra})

    def error(self, message: str, **extra):
        self._logger.error(message, extra={"project": self.project_name, **extra})

    def debug(self, message: str, **extra):
        self._logger.debug(message, extra={"project": self.project_name, **extra})
