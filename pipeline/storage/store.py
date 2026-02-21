"""File-based storage layer for project data with metadata indexing."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from shared.models.data import DataRecord
from shared.utils.files import load_json, save_json, load_yaml, save_yaml
from shared.utils.logging import get_logger

logger = get_logger("storage")


class DataStore:
    """File-based data store for a project's data assets.

    Provides indexing, querying, versioning, and export capabilities
    on top of the file-system storage.
    """

    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.raw_dir = project_path / "data" / "raw"
        self.processed_dir = project_path / "data" / "processed"
        self._index_path = project_path / "data" / "index.json"
        self._index: dict[str, dict] = {}
        self._load_index()

    def _load_index(self):
        """Load the data index from disk."""
        data = load_json(self._index_path)
        self._index = data.get("records", {}) if data else {}

    def _save_index(self):
        """Persist the data index to disk."""
        save_json(self._index_path, {
            "records": self._index,
            "count": len(self._index),
            "updated_at": datetime.utcnow().isoformat() + "Z",
        })

    def add_records(self, records: list[DataRecord]):
        """Add records to the index."""
        for record in records:
            self._index[record.id] = {
                "id": record.id,
                "title": record.title,
                "source_url": record.source_url,
                "quality_score": record.quality_score,
                "source_type": record.provenance.source_type,
                "indexed_at": datetime.utcnow().isoformat() + "Z",
            }
        self._save_index()
        logger.info("Indexed %d records (total: %d)", len(records), len(self._index))

    def get_record(self, record_id: str) -> dict | None:
        """Get index entry for a record by ID."""
        return self._index.get(record_id)

    def search(
        self,
        source_type: str | None = None,
        min_quality: float = 0.0,
        limit: int = 100,
    ) -> list[dict]:
        """Query the index with optional filters."""
        results = []
        for entry in self._index.values():
            if source_type and entry.get("source_type") != source_type:
                continue
            if entry.get("quality_score", 0) < min_quality:
                continue
            results.append(entry)
            if len(results) >= limit:
                break
        return results

    @property
    def record_count(self) -> int:
        return len(self._index)

    def get_processed_records(self) -> list[DataRecord]:
        """Load all processed records from the processed data file."""
        json_path = self.processed_dir / "dataset.json"
        data = load_json(json_path)
        if not data:
            return []
        if isinstance(data, list):
            return [DataRecord.from_dict(d) for d in data]
        return []

    def export_csv(self, output_path: Path, fields: list[str] | None = None):
        """Export processed data as CSV."""
        import csv

        records = self.get_processed_records()
        if not records:
            logger.warning("No processed records to export")
            return

        if fields is None:
            fields = ["id", "title", "source_url", "quality_score"]

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            for record in records:
                row = {}
                rd = record.to_dict()
                for field in fields:
                    row[field] = rd.get(field, "")
                writer.writerow(row)
        logger.info("Exported %d records to %s", len(records), output_path)

    def get_summary(self) -> dict:
        """Return a summary of the data store."""
        by_type: dict[str, int] = {}
        total_quality = 0.0
        for entry in self._index.values():
            st = entry.get("source_type", "unknown")
            by_type[st] = by_type.get(st, 0) + 1
            total_quality += entry.get("quality_score", 0)

        avg_quality = total_quality / len(self._index) if self._index else 0
        return {
            "total_records": len(self._index),
            "by_source_type": by_type,
            "average_quality_score": round(avg_quality, 4),
            "raw_files": len(list(self.raw_dir.glob("*.json"))) if self.raw_dir.exists() else 0,
            "processed_files": len(list(self.processed_dir.glob("*"))) if self.processed_dir.exists() else 0,
        }
