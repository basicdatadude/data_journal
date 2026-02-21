"""Report data models."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


class ReportStatus(enum.Enum):
    DRAFTING = "drafting"
    QUALITY_CHECK = "quality_check"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REVISION = "revision"


WHITEPAPER_SECTIONS = [
    "title_page",
    "abstract",
    "introduction",
    "literature_review",
    "methodology",
    "results",
    "discussion",
    "conclusion",
    "references",
    "appendices",
]


@dataclass
class Citation:
    key: str  # e.g. "Smith2024"
    authors: list[str] = field(default_factory=list)
    title: str = ""
    year: str = ""
    source: str = ""  # journal, website, etc.
    url: str = ""
    doi: str = ""
    accessed_date: str = ""

    def format_apa(self) -> str:
        authors_str = ", ".join(self.authors) if self.authors else "Unknown"
        year_str = f"({self.year})" if self.year else "(n.d.)"
        title_str = f"*{self.title}*" if self.title else ""
        source_str = self.source or ""
        parts = [p for p in [authors_str, year_str, title_str, source_str] if p]
        formatted = ". ".join(parts)
        if self.url:
            formatted += f" Retrieved from {self.url}"
        return formatted

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "authors": self.authors,
            "title": self.title,
            "year": self.year,
            "source": self.source,
            "url": self.url,
            "doi": self.doi,
            "accessed_date": self.accessed_date,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Citation:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ReportSection:
    name: str
    title: str = ""
    content: str = ""
    word_count: int = 0
    figures: list[str] = field(default_factory=list)
    tables: list[str] = field(default_factory=list)
    citations_used: list[str] = field(default_factory=list)

    def __post_init__(self):
        if self.content and not self.word_count:
            self.word_count = len(self.content.split())

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "title": self.title,
            "content": self.content,
            "word_count": self.word_count,
            "figures": self.figures,
            "tables": self.tables,
            "citations_used": self.citations_used,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ReportSection:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class Report:
    project_name: str
    title: str = ""
    status: ReportStatus = ReportStatus.DRAFTING
    version: int = 1
    sections: list[ReportSection] = field(default_factory=list)
    citations: list[Citation] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if isinstance(self.status, str):
            self.status = ReportStatus(self.status)
        now = datetime.utcnow().isoformat() + "Z"
        if not self.created_at:
            self.created_at = now
        self.updated_at = now

    @property
    def total_word_count(self) -> int:
        return sum(s.word_count for s in self.sections)

    @property
    def abstract_word_count(self) -> int:
        for s in self.sections:
            if s.name == "abstract":
                return s.word_count
        return 0

    @property
    def body_word_count(self) -> int:
        body_sections = {"introduction", "literature_review", "methodology",
                         "results", "discussion", "conclusion"}
        return sum(s.word_count for s in self.sections if s.name in body_sections)

    @property
    def all_citation_keys(self) -> set[str]:
        keys: set[str] = set()
        for s in self.sections:
            keys.update(s.citations_used)
        return keys

    @property
    def reference_keys(self) -> set[str]:
        return {c.key for c in self.citations}

    @property
    def missing_references(self) -> set[str]:
        return self.all_citation_keys - self.reference_keys

    @property
    def orphan_references(self) -> set[str]:
        return self.reference_keys - self.all_citation_keys

    def get_section(self, name: str) -> ReportSection | None:
        for s in self.sections:
            if s.name == name:
                return s
        return None

    def set_section(self, section: ReportSection):
        for i, s in enumerate(self.sections):
            if s.name == section.name:
                self.sections[i] = section
                return
        self.sections.append(section)

    def compile_markdown(self) -> str:
        parts: list[str] = []
        for section in self.sections:
            if section.name == "title_page":
                parts.append(f"# {self.title}\n")
                if section.content:
                    parts.append(section.content)
            elif section.name == "references":
                parts.append(f"## References\n")
                for citation in sorted(self.citations, key=lambda c: c.key):
                    parts.append(f"- [{citation.key}] {citation.format_apa()}")
            else:
                heading = section.title or section.name.replace("_", " ").title()
                parts.append(f"## {heading}\n")
                if section.content:
                    parts.append(section.content)
            parts.append("")  # blank line between sections
        return "\n".join(parts)

    def to_dict(self) -> dict:
        return {
            "project_name": self.project_name,
            "title": self.title,
            "status": self.status.value,
            "version": self.version,
            "sections": [s.to_dict() for s in self.sections],
            "citations": [c.to_dict() for c in self.citations],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "total_word_count": self.total_word_count,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Report:
        return cls(
            project_name=data.get("project_name", ""),
            title=data.get("title", ""),
            status=data.get("status", "drafting"),
            version=data.get("version", 1),
            sections=[ReportSection.from_dict(s) for s in data.get("sections", [])],
            citations=[Citation.from_dict(c) for c in data.get("citations", [])],
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            metadata=data.get("metadata", {}),
        )
