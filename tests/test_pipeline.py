"""Tests for the data pipeline."""

import tempfile
from pathlib import Path

import pytest
from shared.models.data import DataRecord, Provenance
from pipeline.ingest.pipeline import (
    IngestionPipeline,
    TextCleaner,
    DateNormalizer,
    Deduplicator,
    QualityScorer,
)
from pipeline.storage.store import DataStore


class TestTextCleaner:
    def test_clean_whitespace(self):
        text = "hello   world  \n\n\n\n\nfoo"
        result = TextCleaner.clean(text)
        assert "   " not in result
        assert "\n\n\n" not in result

    def test_remove_html(self):
        text = "<p>Hello <b>world</b></p>"
        result = TextCleaner.remove_html(text)
        assert result == "Hello world"

    def test_empty_string(self):
        assert TextCleaner.clean("") == ""
        assert TextCleaner.clean("   ") == ""


class TestDateNormalizer:
    def test_iso_format(self):
        assert DateNormalizer.normalize("2024-01-15") == "2024-01-15"

    def test_us_format(self):
        assert DateNormalizer.normalize("01/15/2024") == "2024-01-15"

    def test_empty(self):
        assert DateNormalizer.normalize("") == ""


class TestDeduplicator:
    def test_detects_exact_duplicate(self):
        dedup = Deduplicator()
        r1 = DataRecord(content="Hello world")
        r2 = DataRecord(content="Hello world")
        assert not dedup.is_duplicate(r1)
        assert dedup.is_duplicate(r2)

    def test_detects_near_duplicate(self):
        dedup = Deduplicator()
        r1 = DataRecord(content="Hello World")
        r2 = DataRecord(content="hello world")  # Same content, different case
        assert not dedup.is_duplicate(r1)
        assert dedup.is_duplicate(r2)  # Normalized to same hash

    def test_unique_records(self):
        dedup = Deduplicator()
        r1 = DataRecord(content="Content A")
        r2 = DataRecord(content="Content B")
        assert not dedup.is_duplicate(r1)
        assert not dedup.is_duplicate(r2)


class TestQualityScorer:
    def test_high_quality(self):
        scorer = QualityScorer()
        record = DataRecord(
            content="This is a substantial piece of content " * 20,
            title="Good Title",
            source_url="https://example.com",
            provenance=Provenance(
                source_url="https://example.com",
                content_hash="sha256:abc",
                crawler="web_search",
            ),
        )
        metrics = scorer.score(record)
        assert metrics.overall > 0.5

    def test_low_quality(self):
        scorer = QualityScorer()
        record = DataRecord(content="short")
        metrics = scorer.score(record)
        assert metrics.completeness < 0.5
        assert metrics.accuracy < 0.5


class TestIngestionPipeline:
    def test_ingest_records(self, tmp_path):
        pipeline = IngestionPipeline(tmp_path)
        records = [
            DataRecord(
                content="Article about machine learning " * 20,
                title="ML Article",
                source_url="https://example.com/1",
                provenance=Provenance(source_url="https://example.com/1", crawler="web"),
            ),
            DataRecord(
                content="Article about data science " * 20,
                title="DS Article",
                source_url="https://example.com/2",
                provenance=Provenance(source_url="https://example.com/2", crawler="web"),
            ),
        ]
        processed = pipeline.ingest(records)
        assert len(processed) == 2
        assert (tmp_path / "data" / "processed" / "dataset.json").exists()

    def test_dedup_during_ingest(self, tmp_path):
        pipeline = IngestionPipeline(tmp_path)
        records = [
            DataRecord(content="Identical content here " * 10, title="A", source_url="u1"),
            DataRecord(content="Identical content here " * 10, title="B", source_url="u2"),
        ]
        processed = pipeline.ingest(records)
        assert len(processed) == 1

    def test_skip_empty(self, tmp_path):
        pipeline = IngestionPipeline(tmp_path)
        records = [
            DataRecord(content="", title="Empty"),
            DataRecord(content="Valid content " * 10, title="Valid"),
        ]
        processed = pipeline.ingest(records)
        assert len(processed) == 1


class TestDataStore:
    def test_add_and_query(self, tmp_path):
        (tmp_path / "data" / "raw").mkdir(parents=True)
        (tmp_path / "data" / "processed").mkdir(parents=True)
        store = DataStore(tmp_path)

        records = [
            DataRecord(content="Content A", provenance=Provenance(source_type="web_page")),
            DataRecord(content="Content B", provenance=Provenance(source_type="academic_paper")),
        ]
        store.add_records(records)

        assert store.record_count == 2
        results = store.search(source_type="web_page")
        assert len(results) == 1

    def test_summary(self, tmp_path):
        (tmp_path / "data" / "raw").mkdir(parents=True)
        (tmp_path / "data" / "processed").mkdir(parents=True)
        store = DataStore(tmp_path)

        records = [DataRecord(content="Test", quality_score=0.8)]
        store.add_records(records)

        summary = store.get_summary()
        assert summary["total_records"] == 1
        assert summary["average_quality_score"] == 0.8
