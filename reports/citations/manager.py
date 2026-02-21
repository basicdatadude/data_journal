"""Citation management: collect, format, validate, and integrate references."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from shared.models.report import Citation, Report
from shared.utils.files import load_yaml, save_yaml
from shared.utils.logging import get_logger

logger = get_logger("citations")


class CitationManager:
    """Manage citations and references for a research project."""

    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.bib_path = project_path / "references" / "bibliography.yaml"
        self._citations: dict[str, Citation] = {}
        self._load()

    def _load(self):
        """Load citations from the bibliography file."""
        data = load_yaml(self.bib_path)
        for ref in data.get("references", []):
            citation = Citation.from_dict(ref)
            self._citations[citation.key] = citation

    def save(self):
        """Save citations to the bibliography file."""
        refs = [c.to_dict() for c in sorted(self._citations.values(), key=lambda c: c.key)]
        save_yaml(self.bib_path, {"references": refs})

    def add(self, citation: Citation):
        """Add or update a citation."""
        self._citations[citation.key] = citation
        self.save()

    def remove(self, key: str):
        """Remove a citation by key."""
        self._citations.pop(key, None)
        self.save()

    def get(self, key: str) -> Citation | None:
        """Get a citation by key."""
        return self._citations.get(key)

    def list_all(self) -> list[Citation]:
        """List all citations sorted by key."""
        return sorted(self._citations.values(), key=lambda c: c.key)

    @property
    def count(self) -> int:
        return len(self._citations)

    def validate_report(self, report: Report) -> dict:
        """Validate citations in a report.

        Returns a dict with:
        - missing_references: citation keys used in text but not in bibliography
        - orphan_references: keys in bibliography but not cited in text
        - valid: True if no issues found
        """
        cited_keys = report.all_citation_keys
        ref_keys = {c.key for c in self._citations.values()}

        missing = cited_keys - ref_keys
        orphans = ref_keys - cited_keys

        return {
            "valid": len(missing) == 0,
            "missing_references": sorted(missing),
            "orphan_references": sorted(orphans),
            "total_cited": len(cited_keys),
            "total_in_bibliography": len(ref_keys),
        }

    def format_reference_list(self, format_style: str = "apa") -> str:
        """Generate a formatted reference list."""
        lines = []
        for citation in sorted(self._citations.values(), key=lambda c: c.key):
            if format_style == "apa":
                lines.append(f"[{citation.key}] {citation.format_apa()}")
            else:
                # Default to simple format
                lines.append(f"[{citation.key}] {citation.format_apa()}")
        return "\n".join(lines)

    def create_from_data_record(self, record_dict: dict, key: str = "") -> Citation:
        """Create a citation from a data record's provenance info."""
        prov = record_dict.get("provenance", {})
        if not key:
            # Generate a key from the URL or title
            title = record_dict.get("title", "")
            words = title.split()[:2] if title else ["Source"]
            year = prov.get("access_date", "")[:4] or "n.d."
            key = "".join(w.capitalize() for w in words) + year

        return Citation(
            key=key,
            title=record_dict.get("title", ""),
            url=prov.get("source_url", record_dict.get("source_url", "")),
            accessed_date=prov.get("access_date", ""),
            source=prov.get("source_type", ""),
        )
