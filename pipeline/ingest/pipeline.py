"""Data ingestion pipeline: extract, clean, normalize, deduplicate, validate, store."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any

from shared.models.data import DataRecord, QualityMetrics
from shared.utils.files import append_jsonl, save_json, save_yaml
from shared.utils.logging import get_logger

logger = get_logger("ingest")


class TextCleaner:
    """Clean and normalize text content."""

    @staticmethod
    def clean(text: str) -> str:
        if not text:
            return ""
        # Normalize unicode
        text = unicodedata.normalize("NFKC", text)
        # Remove control characters (except newlines and tabs)
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
        # Collapse multiple whitespace (preserving newlines)
        text = re.sub(r"[^\S\n]+", " ", text)
        # Collapse multiple newlines into at most two
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    @staticmethod
    def remove_html(text: str) -> str:
        """Strip any remaining HTML tags."""
        return re.sub(r"<[^>]+>", "", text)

    @staticmethod
    def normalize_whitespace(text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()


class DateNormalizer:
    """Normalize date strings to ISO 8601 format."""

    COMMON_FORMATS = [
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S%z",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%B %d, %Y",
        "%b %d, %Y",
        "%d %B %Y",
        "%d %b %Y",
        "%Y%m%d",
    ]

    @classmethod
    def normalize(cls, date_str: str) -> str:
        """Attempt to parse and normalize a date string to ISO 8601."""
        if not date_str:
            return ""
        date_str = date_str.strip()
        for fmt in cls.COMMON_FORMATS:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue
        return date_str  # Return as-is if no format matches


class Deduplicator:
    """Detect and remove duplicate records."""

    def __init__(self):
        self._seen_hashes: set[str] = set()

    def _content_hash(self, text: str) -> str:
        normalized = TextCleaner.normalize_whitespace(text.lower())
        return hashlib.md5(normalized.encode()).hexdigest()

    def is_duplicate(self, record: DataRecord) -> bool:
        """Check if a record is a duplicate of one already seen."""
        h = self._content_hash(record.content)
        if h in self._seen_hashes:
            return True
        self._seen_hashes.add(h)
        return False

    def reset(self):
        self._seen_hashes.clear()


class QualityScorer:
    """Score data records on quality dimensions."""

    def score(self, record: DataRecord) -> QualityMetrics:
        return QualityMetrics(
            completeness=self._score_completeness(record),
            accuracy=self._score_accuracy(record),
            timeliness=self._score_timeliness(record),
            consistency=self._score_consistency(record),
            provenance_score=self._score_provenance(record),
        )

    def _score_completeness(self, record: DataRecord) -> float:
        """Score based on how many fields are populated."""
        fields = [record.content, record.title, record.source_url]
        filled = sum(1 for f in fields if f and f.strip())
        return filled / len(fields)

    def _score_accuracy(self, record: DataRecord) -> float:
        """Basic accuracy heuristic: content length and structure."""
        content = record.content
        if not content:
            return 0.0
        word_count = len(content.split())
        if word_count < 50:
            return 0.3
        if word_count < 200:
            return 0.6
        return 0.9

    def _score_timeliness(self, record: DataRecord) -> float:
        """Score based on how recent the access date is."""
        access_date = record.provenance.access_date
        if not access_date:
            return 0.5
        try:
            access = datetime.fromisoformat(access_date.replace("Z", "+00:00"))
            age_days = (datetime.now(access.tzinfo) - access).days
            if age_days < 30:
                return 1.0
            if age_days < 180:
                return 0.8
            if age_days < 365:
                return 0.6
            return 0.4
        except (ValueError, TypeError):
            return 0.5

    def _score_consistency(self, record: DataRecord) -> float:
        """Placeholder — in production, cross-reference with other records."""
        return 0.7

    def _score_provenance(self, record: DataRecord) -> float:
        """Score based on provenance metadata completeness."""
        prov = record.provenance
        fields = [prov.source_url, prov.access_date, prov.content_hash, prov.crawler]
        filled = sum(1 for f in fields if f)
        base = filled / len(fields)
        return min(1.0, base + prov.reliability_score * 0.2)


class IngestionPipeline:
    """Full ingestion pipeline: clean, normalize, deduplicate, score, store."""

    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.raw_dir = project_path / "data" / "raw"
        self.processed_dir = project_path / "data" / "processed"
        self.errors_dir = project_path / "data" / "errors"
        self.cleaner = TextCleaner()
        self.deduplicator = Deduplicator()
        self.scorer = QualityScorer()
        self._log_path = project_path / "data" / "processed" / "ingestion_log.jsonl"

    def ingest(self, records: list[DataRecord]) -> list[DataRecord]:
        """Process a batch of raw records through the full pipeline.

        Returns the list of successfully processed records.
        """
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        self.errors_dir.mkdir(parents=True, exist_ok=True)

        processed: list[DataRecord] = []
        stats = {"total": len(records), "processed": 0, "duplicates": 0, "errors": 0}

        for record in records:
            try:
                # Clean
                record.content = self.cleaner.clean(record.content)
                record.content = self.cleaner.remove_html(record.content)
                record.title = self.cleaner.clean(record.title)

                # Skip empty
                if not record.content.strip():
                    stats["errors"] += 1
                    self._log_event("skip_empty", record)
                    continue

                # Deduplicate
                if self.deduplicator.is_duplicate(record):
                    stats["duplicates"] += 1
                    self._log_event("duplicate", record)
                    continue

                # Score quality
                metrics = self.scorer.score(record)
                record.quality_score = metrics.overall

                processed.append(record)
                stats["processed"] += 1
                self._log_event("processed", record, quality=metrics.to_dict())

            except Exception as e:
                stats["errors"] += 1
                self._log_event("error", record, error=str(e))
                logger.error("Ingestion error for record %s: %s", record.id, e)

        # Save processed records
        self._save_processed(processed)
        self._save_quality_report(stats, processed)

        logger.info(
            "Ingestion complete: %d processed, %d duplicates, %d errors out of %d total",
            stats["processed"], stats["duplicates"], stats["errors"], stats["total"],
        )
        return processed

    def _save_processed(self, records: list[DataRecord]):
        """Save processed records to the processed directory."""
        # JSON records
        json_path = self.processed_dir / "dataset.json"
        data = [r.to_dict() for r in records]
        save_json(json_path, data)

        # JSONL text corpus
        corpus_path = self.processed_dir / "text_corpus.jsonl"
        for record in records:
            append_jsonl(corpus_path, {
                "id": record.id,
                "title": record.title,
                "content": record.content,
                "source_url": record.source_url,
                "quality_score": record.quality_score,
            })

    def _save_quality_report(self, stats: dict, records: list[DataRecord]):
        """Save a quality summary report."""
        avg_quality = (
            sum(r.quality_score for r in records) / len(records) if records else 0
        )
        report = {
            "ingestion_summary": stats,
            "average_quality_score": round(avg_quality, 4),
            "quality_distribution": {
                "high": sum(1 for r in records if r.quality_score >= 0.7),
                "medium": sum(1 for r in records if 0.4 <= r.quality_score < 0.7),
                "low": sum(1 for r in records if r.quality_score < 0.4),
            },
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        save_yaml(self.processed_dir / "quality_report.yaml", report)

    def _log_event(self, event: str, record: DataRecord, **extra):
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event": event,
            "record_id": record.id,
            "source_url": record.source_url,
            **extra,
        }
        append_jsonl(self._log_path, entry)

    def save_raw(self, records: list[DataRecord]):
        """Save raw crawled records and their provenance metadata."""
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        manifest_entries = []

        for i, record in enumerate(records):
            source_id = f"source_{i + 1:03d}"
            # Save content
            save_json(self.raw_dir / f"{source_id}.json", record.to_dict())
            # Save provenance
            save_yaml(self.raw_dir / f"{source_id}.meta.yaml", {
                "provenance": record.provenance.to_dict()
            })
            manifest_entries.append({
                "id": source_id,
                "record_id": record.id,
                "source_url": record.source_url,
                "title": record.title,
            })

        save_yaml(self.raw_dir / "crawl_manifest.yaml", {"sources": manifest_entries})
