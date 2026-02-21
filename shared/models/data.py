"""Data pipeline models."""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Provenance:
    source_url: str = ""
    source_type: str = "web_page"  # web_page | academic_paper | dataset | news_article
    access_date: str = ""
    content_hash: str = ""
    crawler: str = ""
    query_context: str = ""
    reliability_score: float = 0.5

    def __post_init__(self):
        if not self.access_date:
            self.access_date = datetime.utcnow().isoformat() + "Z"

    def to_dict(self) -> dict:
        return {
            "source_url": self.source_url,
            "source_type": self.source_type,
            "access_date": self.access_date,
            "content_hash": self.content_hash,
            "crawler": self.crawler,
            "query_context": self.query_context,
            "reliability_score": self.reliability_score,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Provenance:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class SearchResult:
    url: str
    title: str
    snippet: str = ""
    rank: int = 0

    def to_dict(self) -> dict:
        return {"url": self.url, "title": self.title, "snippet": self.snippet, "rank": self.rank}


@dataclass
class FetchResult:
    url: str
    content: str
    status_code: int = 200
    headers: dict[str, str] = field(default_factory=dict)
    timestamp: str = ""
    content_type: str = "text/html"

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat() + "Z"

    @property
    def content_hash(self) -> str:
        return f"sha256:{hashlib.sha256(self.content.encode()).hexdigest()}"


@dataclass
class DataRecord:
    id: str = ""
    content: str = ""
    title: str = ""
    source_url: str = ""
    provenance: Provenance = field(default_factory=Provenance)
    quality_score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())[:8]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "content": self.content,
            "title": self.title,
            "source_url": self.source_url,
            "provenance": self.provenance.to_dict(),
            "quality_score": self.quality_score,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> DataRecord:
        prov = data.get("provenance", {})
        return cls(
            id=data.get("id", ""),
            content=data.get("content", ""),
            title=data.get("title", ""),
            source_url=data.get("source_url", ""),
            provenance=Provenance.from_dict(prov) if prov else Provenance(),
            quality_score=data.get("quality_score", 0.0),
            metadata=data.get("metadata", {}),
        )


@dataclass
class QualityMetrics:
    completeness: float = 0.0
    accuracy: float = 0.0
    timeliness: float = 0.0
    consistency: float = 0.0
    provenance_score: float = 0.0

    WEIGHTS = {
        "completeness": 0.25,
        "accuracy": 0.25,
        "timeliness": 0.20,
        "consistency": 0.15,
        "provenance_score": 0.15,
    }

    @property
    def overall(self) -> float:
        return sum(
            getattr(self, k) * w for k, w in self.WEIGHTS.items()
        )

    def to_dict(self) -> dict:
        return {
            "completeness": self.completeness,
            "accuracy": self.accuracy,
            "timeliness": self.timeliness,
            "consistency": self.consistency,
            "provenance_score": self.provenance_score,
            "overall": round(self.overall, 4),
        }
