"""Report composition engine: draft, assemble, and export whitepapers."""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from shared.ai_client.client import AIClient, BudgetContext
from shared.models.report import Report, ReportSection, ReportStatus
from shared.utils.files import save_json, save_yaml, safe_write
from shared.utils.logging import get_logger
from reports.citations.manager import CitationManager
from reports.templates.whitepaper import (
    SECTION_TEMPLATES,
    MARKDOWN_TEMPLATE,
    LATEX_TEMPLATE,
    create_empty_report_sections,
)

logger = get_logger("report_generator")


class ReportComposer:
    """Compose academic whitepapers section by section using AI assistance."""

    def __init__(
        self,
        project_path: Path,
        ai_client: AIClient | None = None,
        budget_context: BudgetContext | None = None,
    ):
        self.project_path = project_path
        self.report_dir = project_path / "report"
        self.drafts_dir = self.report_dir / "drafts"
        self.final_dir = self.report_dir / "final"
        self.assets_dir = self.report_dir / "assets"
        self.ai_client = ai_client
        self.budget_context = budget_context
        self.citation_manager = CitationManager(project_path)

    def create_report(self, project_name: str, title: str = "") -> Report:
        """Initialize a new report with empty sections."""
        report = Report(
            project_name=project_name,
            title=title or f"Research Report: {project_name}",
            sections=create_empty_report_sections(),
        )
        return report

    def draft_section(
        self,
        report: Report,
        section_name: str,
        context: dict[str, Any] | None = None,
    ) -> ReportSection:
        """Draft a single section using AI assistance.

        Args:
            report: The report being composed.
            section_name: Name of the section to draft.
            context: Additional context (research questions, data summaries,
                     analysis results, etc.) to inform the draft.
        """
        template = SECTION_TEMPLATES.get(section_name, {})
        guidance = template.get("guidance", "")

        if not self.ai_client:
            # Without AI client, create a placeholder
            return ReportSection(
                name=section_name,
                title=template.get("title", section_name.replace("_", " ").title()),
                content=f"[AI-generated content for {section_name} will appear here]\n\n"
                        f"Guidance: {guidance}",
            )

        # Build the prompt
        context = context or {}
        prompt = self._build_section_prompt(report, section_name, template, context)

        system = (
            "You are an academic research writer producing a section of a whitepaper. "
            "Write in formal academic tone. Support all claims with evidence. "
            "Use clear, precise language. Do not use first person. "
            "Include inline citations in [AuthorYear] format where appropriate."
        )

        response = self.ai_client.generate(
            prompt=prompt,
            system=system,
            temperature=0.3,
            budget_context=self.budget_context,
            task=f"draft_{section_name}",
            project=report.project_name,
        )

        section = ReportSection(
            name=section_name,
            title=template.get("title", section_name.replace("_", " ").title()),
            content=response.text,
        )
        report.set_section(section)
        return section

    def _build_section_prompt(
        self,
        report: Report,
        section_name: str,
        template: dict,
        context: dict,
    ) -> str:
        parts = [
            f"Write the '{template.get('title', section_name)}' section of an academic whitepaper.",
            f"\nPaper title: {report.title}",
        ]

        if template.get("guidance"):
            parts.append(f"\nGuidance: {template['guidance']}")

        if template.get("min_words"):
            parts.append(f"\nMinimum length: {template['min_words']} words")

        if context.get("research_questions"):
            parts.append("\nResearch questions:")
            for q in context["research_questions"]:
                parts.append(f"  - {q}")

        if context.get("data_summary"):
            parts.append(f"\nData summary:\n{context['data_summary']}")

        if context.get("analysis_results"):
            parts.append(f"\nAnalysis results:\n{context['analysis_results']}")

        if context.get("key_findings"):
            parts.append("\nKey findings:")
            for f in context["key_findings"]:
                parts.append(f"  - {f}")

        if context.get("previous_sections"):
            parts.append(f"\nPrevious sections for context:\n{context['previous_sections']}")

        return "\n".join(parts)

    def draft_all_sections(
        self, report: Report, context: dict[str, Any] | None = None
    ) -> Report:
        """Draft all sections of the report."""
        context = context or {}
        built_context = ""

        for section_name in [s.name for s in report.sections]:
            if section_name == "references":
                # References are generated from the citation manager
                ref_content = self.citation_manager.format_reference_list()
                report.set_section(ReportSection(
                    name="references", title="References", content=ref_content,
                ))
                continue

            section_context = {**context, "previous_sections": built_context}
            section = self.draft_section(report, section_name, section_context)

            # Accumulate context for later sections
            if section.content and section.name != "title_page":
                built_context += f"\n\n## {section.title}\n{section.content[:500]}..."

        report.status = ReportStatus.QUALITY_CHECK
        return report

    def save_draft(self, report: Report) -> Path:
        """Save the current report as a versioned draft."""
        version_dir = self.drafts_dir / f"v{report.version}"
        version_dir.mkdir(parents=True, exist_ok=True)

        # Save as markdown
        md_path = version_dir / "whitepaper.md"
        md_content = self._compile_markdown(report)
        safe_write(md_path, md_content)

        # Save report metadata
        save_json(version_dir / "report_meta.json", report.to_dict())

        logger.info("Saved draft v%d to %s", report.version, version_dir)
        return version_dir

    def save_final(self, report: Report) -> Path:
        """Save the approved final version."""
        self.final_dir.mkdir(parents=True, exist_ok=True)

        # Markdown
        md_path = self.final_dir / "whitepaper.md"
        md_content = self._compile_markdown(report)
        safe_write(md_path, md_content)

        # LaTeX source
        tex_path = self.final_dir / "whitepaper.tex"
        tex_content = self._compile_latex(report)
        safe_write(tex_path, tex_content)

        # Report metadata
        save_json(self.final_dir / "report_meta.json", report.to_dict())

        # Copy figures to assets
        figures_src = self.project_path / "analysis" / "outputs" / "figures"
        figures_dst = self.assets_dir / "figures"
        if figures_src.exists():
            figures_dst.mkdir(parents=True, exist_ok=True)
            for fig in figures_src.iterdir():
                if fig.is_file():
                    shutil.copy2(fig, figures_dst / fig.name)

        logger.info("Saved final report to %s", self.final_dir)
        return self.final_dir

    def revise_section(
        self,
        report: Report,
        section_name: str,
        feedback: str,
        context: dict[str, Any] | None = None,
    ) -> ReportSection:
        """Revise a specific section based on feedback."""
        current = report.get_section(section_name)
        if not current:
            return self.draft_section(report, section_name, context)

        if not self.ai_client:
            current.content += f"\n\n[Revision needed: {feedback}]"
            return current

        prompt = (
            f"Revise the following section of an academic whitepaper based on the feedback.\n\n"
            f"Section: {current.title}\n"
            f"Current content:\n{current.content}\n\n"
            f"Feedback:\n{feedback}\n\n"
            f"Write the revised section. Maintain academic tone and proper citations."
        )

        response = self.ai_client.generate(
            prompt=prompt,
            system="You are an academic research writer revising a whitepaper section.",
            budget_context=self.budget_context,
            task=f"revise_{section_name}",
            project=report.project_name,
        )

        section = ReportSection(
            name=section_name,
            title=current.title,
            content=response.text,
        )
        report.set_section(section)
        return section

    def _compile_markdown(self, report: Report) -> str:
        """Compile the report to a markdown document."""
        sections_content = {}
        for section in report.sections:
            sections_content[section.name] = section.content or ""

        return MARKDOWN_TEMPLATE.format(
            title=report.title,
            date=datetime.now().strftime("%Y-%m-%d"),
            project_name=report.project_name,
            abstract=sections_content.get("abstract", ""),
            introduction=sections_content.get("introduction", ""),
            literature_review=sections_content.get("literature_review", ""),
            methodology=sections_content.get("methodology", ""),
            results=sections_content.get("results", ""),
            discussion=sections_content.get("discussion", ""),
            conclusion=sections_content.get("conclusion", ""),
            references=sections_content.get("references", ""),
            appendices=sections_content.get("appendices", ""),
        )

    def _compile_latex(self, report: Report) -> str:
        """Compile the report to LaTeX source."""
        sections_content = {}
        for section in report.sections:
            content = section.content or ""
            # Escape LaTeX special characters
            for char in ["&", "%", "$", "#", "_"]:
                content = content.replace(char, f"\\{char}")
            sections_content[section.name] = content

        return LATEX_TEMPLATE.format(
            title=report.title,
            date=datetime.now().strftime("%Y-%m-%d"),
            abstract=sections_content.get("abstract", ""),
            introduction=sections_content.get("introduction", ""),
            literature_review=sections_content.get("literature_review", ""),
            methodology=sections_content.get("methodology", ""),
            results=sections_content.get("results", ""),
            discussion=sections_content.get("discussion", ""),
            conclusion=sections_content.get("conclusion", ""),
            appendices=sections_content.get("appendices", ""),
        )
