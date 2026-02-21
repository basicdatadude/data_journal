"""Tests for shared data models."""

import pytest
from shared.models.project import ProjectConfig, ProjectStatus, Priority, BudgetConfig
from shared.models.data import DataRecord, Provenance, QualityMetrics
from shared.models.agent import AgentState, AgentPhase, AgentMemory
from shared.models.report import Report, ReportSection, Citation, ReportStatus
from shared.models.events import Event, EventType


class TestProjectConfig:
    def test_create_minimal(self):
        config = ProjectConfig(name="test-project", topic="Test Topic")
        assert config.name == "test-project"
        assert config.status == ProjectStatus.CREATED
        assert config.priority == Priority.NORMAL

    def test_roundtrip(self):
        config = ProjectConfig(
            name="test", topic="Test", description="A test",
            research_questions=["Q1?", "Q2?"],
            tags=["tag1"],
        )
        d = config.to_dict()
        restored = ProjectConfig.from_dict(d)
        assert restored.name == config.name
        assert restored.topic == config.topic
        assert restored.research_questions == config.research_questions

    def test_status_string_conversion(self):
        config = ProjectConfig(name="t", topic="t", status="active")
        assert config.status == ProjectStatus.ACTIVE


class TestDataRecord:
    def test_create_with_auto_id(self):
        record = DataRecord(content="Hello world")
        assert record.id
        assert record.content == "Hello world"

    def test_roundtrip(self):
        record = DataRecord(
            content="Test content",
            title="Test Title",
            source_url="https://example.com",
            provenance=Provenance(source_url="https://example.com", source_type="web_page"),
        )
        d = record.to_dict()
        restored = DataRecord.from_dict(d)
        assert restored.content == record.content
        assert restored.provenance.source_type == "web_page"


class TestQualityMetrics:
    def test_overall_score(self):
        m = QualityMetrics(
            completeness=1.0,
            accuracy=1.0,
            timeliness=1.0,
            consistency=1.0,
            provenance_score=1.0,
        )
        assert m.overall == pytest.approx(1.0)

    def test_weighted_score(self):
        m = QualityMetrics(
            completeness=0.5,
            accuracy=0.5,
            timeliness=0.5,
            consistency=0.5,
            provenance_score=0.5,
        )
        assert m.overall == pytest.approx(0.5)


class TestAgentState:
    def test_create_default(self):
        state = AgentState(project_name="test")
        assert state.phase == AgentPhase.IDLE
        assert state.started_at

    def test_transition(self):
        state = AgentState(project_name="test")
        state.transition(AgentPhase.PLAN)
        assert state.phase == AgentPhase.PLAN

    def test_roundtrip(self):
        state = AgentState(project_name="test", phase=AgentPhase.COLLECT)
        state.memory.add_finding("Found something", source="test")
        d = state.to_dict()
        restored = AgentState.from_dict(d)
        assert restored.phase == AgentPhase.COLLECT
        assert len(restored.memory.findings) == 1


class TestReport:
    def test_create(self):
        report = Report(project_name="test", title="Test Report")
        assert report.status == ReportStatus.DRAFTING
        assert report.version == 1

    def test_word_count(self):
        report = Report(project_name="test")
        report.set_section(ReportSection(
            name="abstract", title="Abstract", content="word " * 200,
        ))
        report.set_section(ReportSection(
            name="introduction", title="Introduction", content="word " * 500,
        ))
        assert report.abstract_word_count == 200
        assert report.body_word_count == 500

    def test_citation_tracking(self):
        report = Report(project_name="test")
        report.set_section(ReportSection(
            name="introduction",
            title="Introduction",
            content="As shown by [Smith2024]",
            citations_used=["Smith2024"],
        ))
        report.citations.append(Citation(key="Smith2024", title="Test Paper"))
        assert report.missing_references == set()
        assert report.orphan_references == set()

    def test_missing_references(self):
        report = Report(project_name="test")
        report.set_section(ReportSection(
            name="intro", title="Intro",
            citations_used=["Smith2024", "Jones2025"],
        ))
        report.citations.append(Citation(key="Smith2024"))
        assert "Jones2025" in report.missing_references


class TestEvent:
    def test_create(self):
        event = Event(event_type=EventType.PROJECT_CREATED, project_name="test")
        assert event.timestamp
        assert event.event_type == EventType.PROJECT_CREATED

    def test_serialization(self):
        event = Event(
            event_type=EventType.AGENT_STARTED,
            project_name="test",
            agent_id="agent-123",
            data={"detail": "value"},
        )
        json_str = event.to_json()
        restored = Event.from_dict(__import__("json").loads(json_str))
        assert restored.event_type == EventType.AGENT_STARTED
        assert restored.agent_id == "agent-123"
