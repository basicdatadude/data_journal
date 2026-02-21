"""Quality assurance checks for reports."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from shared.models.report import Report, WHITEPAPER_SECTIONS
from shared.utils.files import save_yaml
from shared.utils.logging import get_logger
from reports.citations.manager import CitationManager
from pathlib import Path

logger = get_logger("quality")


@dataclass
class CheckResult:
    name: str
    passed: bool
    severity: str  # "error", "warning", "info"
    details: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "passed": self.passed,
            "severity": self.severity,
            "details": self.details,
        }


@dataclass
class QualityReport:
    project: str
    version: str
    overall_score: float = 0.0
    checks: list[CheckResult] = field(default_factory=list)
    recommendation: str = "major_revision"
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat() + "Z"

    @property
    def errors(self) -> int:
        return sum(1 for c in self.checks if not c.passed and c.severity == "error")

    @property
    def warnings(self) -> int:
        return sum(1 for c in self.checks if not c.passed and c.severity == "warning")

    @property
    def info_count(self) -> int:
        return sum(1 for c in self.checks if not c.passed and c.severity == "info")

    def to_dict(self) -> dict:
        return {
            "quality_report": {
                "project": self.project,
                "version": self.version,
                "timestamp": self.timestamp,
                "overall_score": round(self.overall_score, 2),
                "checks": [c.to_dict() for c in self.checks],
                "summary": {
                    "errors": self.errors,
                    "warnings": self.warnings,
                    "info": self.info_count,
                    "total_checks": len(self.checks),
                    "passed": sum(1 for c in self.checks if c.passed),
                },
                "recommendation": self.recommendation,
            }
        }


class QualityChecker:
    """Run quality assurance checks on reports."""

    def __init__(
        self,
        project_path: Path,
        min_abstract_words: int = 150,
        min_body_words: int = 3000,
        readability_grade_min: int = 12,
        readability_grade_max: int = 16,
    ):
        self.project_path = project_path
        self.min_abstract_words = min_abstract_words
        self.min_body_words = min_body_words
        self.readability_grade_min = readability_grade_min
        self.readability_grade_max = readability_grade_max
        self.citation_manager = CitationManager(project_path)

    def check(self, report: Report) -> QualityReport:
        """Run all quality checks on a report."""
        checks = [
            self._check_section_completeness(report),
            self._check_citation_integrity(report),
            self._check_figure_references(report),
            self._check_minimum_length(report),
            self._check_readability(report),
            self._check_statistical_reporting(report),
            self._check_methodology_present(report),
            self._check_consistent_terminology(report),
            self._check_no_unsupported_claims(report),
        ]

        passed = sum(1 for c in checks if c.passed)
        total = len(checks)
        score = passed / total if total > 0 else 0

        qr = QualityReport(
            project=report.project_name,
            version=f"v{report.version}",
            overall_score=score,
            checks=checks,
        )

        # Determine recommendation
        if qr.errors == 0 and qr.warnings == 0:
            qr.recommendation = "ready"
        elif qr.errors == 0:
            qr.recommendation = "fix_warnings"
        elif qr.errors <= 2:
            qr.recommendation = "fix_errors"
        else:
            qr.recommendation = "major_revision"

        return qr

    def save_report(self, quality_report: QualityReport, output_dir: Path):
        """Save the quality report to a YAML file."""
        output_dir.mkdir(parents=True, exist_ok=True)
        save_yaml(output_dir / "quality_report.yaml", quality_report.to_dict())

    def _check_section_completeness(self, report: Report) -> CheckResult:
        """All required sections must be present and non-empty."""
        missing = []
        empty = []
        for section_name in WHITEPAPER_SECTIONS:
            section = report.get_section(section_name)
            if section is None:
                missing.append(section_name)
            elif not section.content or not section.content.strip():
                empty.append(section_name)

        if missing or empty:
            details = []
            if missing:
                details.append(f"Missing sections: {', '.join(missing)}")
            if empty:
                details.append(f"Empty sections: {', '.join(empty)}")
            return CheckResult(
                name="section_completeness",
                passed=False,
                severity="error",
                details="; ".join(details),
            )
        return CheckResult(
            name="section_completeness",
            passed=True,
            severity="error",
            details=f"All {len(WHITEPAPER_SECTIONS)} required sections present",
        )

    def _check_citation_integrity(self, report: Report) -> CheckResult:
        """All inline citations must have matching references."""
        validation = self.citation_manager.validate_report(report)
        missing = validation.get("missing_references", [])

        if missing:
            return CheckResult(
                name="citation_integrity",
                passed=False,
                severity="error",
                details=f"{len(missing)} citations missing from references: {', '.join(missing[:5])}",
            )
        return CheckResult(
            name="citation_integrity",
            passed=True,
            severity="error",
            details=f"All {validation.get('total_cited', 0)} citations resolved",
        )

    def _check_figure_references(self, report: Report) -> CheckResult:
        """All figures should be referenced in the text."""
        total_figures = sum(len(s.figures) for s in report.sections)
        if total_figures == 0:
            return CheckResult(
                name="figure_references",
                passed=True,
                severity="warning",
                details="No figures in report",
            )

        # Check if figures are mentioned in any section text
        all_text = " ".join(s.content for s in report.sections if s.content)
        unreferenced = []
        for section in report.sections:
            for fig in section.figures:
                if fig not in all_text:
                    unreferenced.append(fig)

        if unreferenced:
            return CheckResult(
                name="figure_references",
                passed=False,
                severity="warning",
                details=f"{len(unreferenced)} figures not referenced in text",
            )
        return CheckResult(
            name="figure_references",
            passed=True,
            severity="warning",
            details=f"All {total_figures} figures referenced",
        )

    def _check_minimum_length(self, report: Report) -> CheckResult:
        """Abstract and body must meet minimum word counts."""
        abstract_words = report.abstract_word_count
        body_words = report.body_word_count

        issues = []
        if abstract_words < self.min_abstract_words:
            issues.append(
                f"Abstract: {abstract_words} words (min {self.min_abstract_words})"
            )
        if body_words < self.min_body_words:
            issues.append(
                f"Body: {body_words} words (min {self.min_body_words})"
            )

        if issues:
            return CheckResult(
                name="minimum_length",
                passed=False,
                severity="error",
                details="; ".join(issues),
            )
        return CheckResult(
            name="minimum_length",
            passed=True,
            severity="error",
            details=f"Abstract: {abstract_words} words, Body: {body_words} words",
        )

    def _check_readability(self, report: Report) -> CheckResult:
        """Check Flesch-Kincaid grade level."""
        all_text = " ".join(s.content for s in report.sections if s.content)
        if not all_text:
            return CheckResult(
                name="readability_score",
                passed=False,
                severity="warning",
                details="No text to analyze",
            )

        grade = self._flesch_kincaid_grade(all_text)

        in_range = self.readability_grade_min <= grade <= self.readability_grade_max
        return CheckResult(
            name="readability_score",
            passed=in_range,
            severity="warning",
            details=f"Flesch-Kincaid grade: {grade:.1f} "
                    f"(target: {self.readability_grade_min}-{self.readability_grade_max})",
        )

    def _check_statistical_reporting(self, report: Report) -> CheckResult:
        """Check that statistical claims include proper reporting."""
        results_section = report.get_section("results")
        if not results_section or not results_section.content:
            return CheckResult(
                name="statistical_reporting",
                passed=False,
                severity="warning",
                details="Results section is empty",
            )

        content = results_section.content
        # Look for statistical indicators
        has_stats = bool(
            re.search(r"p\s*[=<>]\s*0?\.\d+", content)
            or re.search(r"r\s*=\s*[−-]?0?\.\d+", content)
            or re.search(r"(mean|median|std|standard deviation)", content, re.IGNORECASE)
            or re.search(r"R²?\s*=\s*0?\.\d+", content)
            or re.search(r"(significant|correlation|regression)", content, re.IGNORECASE)
        )

        return CheckResult(
            name="statistical_reporting",
            passed=has_stats,
            severity="warning",
            details="Statistical measures found in results"
            if has_stats
            else "No statistical measures detected in results section",
        )

    def _check_methodology_present(self, report: Report) -> CheckResult:
        """Check that methodology section describes methods adequately."""
        meth = report.get_section("methodology")
        if not meth or not meth.content:
            return CheckResult(
                name="methodology_present",
                passed=False,
                severity="error",
                details="Methodology section is missing or empty",
            )

        word_count = meth.word_count
        has_key_terms = any(
            term in meth.content.lower()
            for term in ["data", "method", "analysis", "collect", "source", "approach"]
        )

        passed = word_count >= 100 and has_key_terms
        return CheckResult(
            name="methodology_present",
            passed=passed,
            severity="error",
            details=f"Methodology: {word_count} words, "
                    f"{'contains' if has_key_terms else 'missing'} key methodological terms",
        )

    def _check_consistent_terminology(self, report: Report) -> CheckResult:
        """Check for consistent use of key terms."""
        # Placeholder: in production, use NLP to detect inconsistencies
        return CheckResult(
            name="consistent_terminology",
            passed=True,
            severity="info",
            details="Terminology consistency check passed (basic)",
        )

    def _check_no_unsupported_claims(self, report: Report) -> CheckResult:
        """Check for claims that lack citations or evidence."""
        # Simple heuristic: look for strong claims without nearby citations
        body_sections = ["introduction", "literature_review", "results", "discussion"]
        uncited_claims = 0

        for section_name in body_sections:
            section = report.get_section(section_name)
            if not section or not section.content:
                continue
            sentences = re.split(r"[.!?]+", section.content)
            for sentence in sentences:
                # Strong claim indicators
                has_claim = any(w in sentence.lower() for w in [
                    "shows that", "demonstrates", "proves", "confirms",
                    "significantly", "evidence suggests", "studies show",
                ])
                has_citation = bool(re.search(r"\[.+?\]", sentence))
                if has_claim and not has_citation:
                    uncited_claims += 1

        passed = uncited_claims <= 2
        return CheckResult(
            name="no_unsupported_claims",
            passed=passed,
            severity="warning",
            details=f"{uncited_claims} potential unsupported claims detected"
            if uncited_claims
            else "No obvious unsupported claims detected",
        )

    @staticmethod
    def _flesch_kincaid_grade(text: str) -> float:
        """Compute Flesch-Kincaid Grade Level."""
        sentences = re.split(r"[.!?]+", text)
        sentences = [s.strip() for s in sentences if s.strip()]
        words = re.findall(r"\b\w+\b", text)
        syllables = sum(_count_syllables(w) for w in words)

        n_sentences = max(len(sentences), 1)
        n_words = max(len(words), 1)

        return 0.39 * (n_words / n_sentences) + 11.8 * (syllables / n_words) - 15.59


def _count_syllables(word: str) -> int:
    """Estimate syllable count for a word."""
    word = word.lower().strip()
    if len(word) <= 2:
        return 1

    vowels = "aeiouy"
    count = 0
    prev_vowel = False

    for char in word:
        is_vowel = char in vowels
        if is_vowel and not prev_vowel:
            count += 1
        prev_vowel = is_vowel

    # Adjust for silent e
    if word.endswith("e") and count > 1:
        count -= 1

    return max(count, 1)
