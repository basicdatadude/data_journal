"""Research agent: per-project autonomous researcher."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agents.base.agent import BaseAgent
from shared.ai_client.client import AIClient, BudgetContext
from shared.models.agent import AgentPhase
from shared.models.project import Project
from pipeline.crawlers.web import get_crawler
from pipeline.crawlers.base import RateLimiter
from pipeline.ingest.pipeline import IngestionPipeline
from pipeline.storage.store import DataStore
from analysis.engine import AnalysisEngine
from reports.generator.compose import ReportComposer
from reports.generator.quality import QualityChecker
from reports.citations.manager import CitationManager
from shared.utils.files import save_json, save_yaml


class ResearchAgent(BaseAgent):
    """Autonomous research agent that investigates topics and produces whitepapers."""

    def __init__(
        self,
        project: Project,
        ai_client: AIClient | None = None,
        budget_context: BudgetContext | None = None,
    ):
        super().__init__(project, ai_client, budget_context)
        self.ingestion = IngestionPipeline(project.path)
        self.data_store = DataStore(project.path)
        self.analysis_engine = AnalysisEngine(project.path)
        self.report_composer = ReportComposer(project.path, ai_client, budget_context)
        self.quality_checker = QualityChecker(project.path)
        self.citation_manager = CitationManager(project.path)

    # --- Phase Implementations ---

    def initialize(self) -> dict[str, Any]:
        """Load existing project state and data."""
        self.logger.info("Initializing research agent for: %s", self.project.name)

        # Try to resume from saved state
        resumed = self.load_state()

        # Check existing data
        data_summary = self.data_store.get_summary()

        result = {
            "project": self.project.name,
            "topic": self.project.config.topic,
            "resumed": resumed,
            "existing_data": data_summary,
            "research_questions": self.project.config.research_questions,
        }

        self.logger.info("Initialization complete: %d existing records", data_summary["total_records"])
        return result

    def plan(self) -> dict[str, Any]:
        """Generate a research plan based on the topic and questions."""
        self.logger.info("Creating research plan")

        topic = self.project.config.topic
        questions = self.project.config.research_questions
        data_sources = self.project.config.data_sources

        # Use AI to generate a detailed research plan
        prompt = (
            f"Create a detailed research plan for the following topic:\n\n"
            f"Topic: {topic}\n\n"
            f"Research Questions:\n"
            + "\n".join(f"  {i+1}. {q}" for i, q in enumerate(questions))
            + f"\n\nAvailable data source types: "
            + ", ".join(ds.source_type for ds in data_sources)
            + "\n\nProvide:\n"
            f"1. Key search queries for data collection (at least 5)\n"
            f"2. Specific data types and sources to target\n"
            f"3. Analysis methods to apply\n"
            f"4. Expected outline of the final report\n\n"
            f"Format as JSON with keys: search_queries, data_targets, "
            f"analysis_methods, report_outline"
        )

        try:
            plan_text = self.ai_generate(prompt, task="research_planning")
            # Try to parse as JSON
            try:
                plan = json.loads(plan_text)
            except json.JSONDecodeError:
                # If not valid JSON, wrap it
                plan = {"raw_plan": plan_text, "search_queries": [], "analysis_methods": []}
        except Exception as e:
            self.logger.warning("AI planning failed, using default plan: %s", e)
            plan = self._default_plan()

        self.state.memory.research_plan = plan
        self.state.memory.add_decision(
            "Research plan created",
            f"Generated plan with {len(plan.get('search_queries', []))} search queries",
        )
        self.save_state()

        # Save plan to project
        save_json(self.project.path / "analysis" / "research_plan.json", plan)
        self.logger.info("Research plan created with %d queries", len(plan.get("search_queries", [])))
        return plan

    def collect(self) -> dict[str, Any]:
        """Execute data collection based on the research plan."""
        self.logger.info("Starting data collection")
        self.state.current_task = "data_collection"

        plan = self.state.memory.research_plan
        search_queries = plan.get("search_queries", [])

        # Also include queries from project config data sources
        for ds in self.project.config.data_sources:
            search_queries.extend(ds.queries)

        # Deduplicate
        search_queries = list(dict.fromkeys(search_queries))

        if not search_queries:
            self.logger.warning("No search queries defined, generating from topic")
            search_queries = [
                self.project.config.topic,
                f"{self.project.config.topic} research data",
                f"{self.project.config.topic} statistics",
            ]

        # Crawl with available crawlers
        all_records = []
        rate_limiter = RateLimiter(requests_per_second=1.0, burst_limit=3)

        for ds in self.project.config.data_sources:
            crawler_type = ds.source_type
            try:
                crawler = get_crawler(crawler_type, rate_limiter=rate_limiter)
                queries = ds.queries or search_queries[:3]
                for query in queries:
                    self.logger.info("Crawling %s for: %s", crawler_type, query)
                    try:
                        records = crawler.crawl(query, max_results=5)
                        all_records.extend(records)
                    except Exception as e:
                        self.logger.error("Crawl failed for query '%s': %s", query, e)
            except ValueError as e:
                self.logger.warning("Skipping crawler type %s: %s", crawler_type, e)

        # Save raw data
        if all_records:
            self.ingestion.save_raw(all_records)

        # Run ingestion pipeline
        processed = self.ingestion.ingest(all_records)

        # Index processed records
        self.data_store.add_records(processed)

        # Create citations from collected sources
        for record in processed:
            citation = self.citation_manager.create_from_data_record(record.to_dict())
            self.citation_manager.add(citation)

        result = {
            "total_crawled": len(all_records),
            "processed": len(processed),
            "data_store_total": self.data_store.record_count,
            "sources_used": [ds.source_type for ds in self.project.config.data_sources],
        }

        self.state.memory.add_finding(
            f"Collected {len(all_records)} records, {len(processed)} processed",
            source="data_collection",
        )
        self.state.progress_pct = 30.0
        self.save_state()
        self.logger.info("Data collection complete: %d records", len(processed))
        return result

    def analyze(self) -> dict[str, Any]:
        """Run analyses on collected data."""
        self.logger.info("Starting analysis")
        self.state.current_task = "analysis"

        plan = self.state.memory.research_plan
        methods = plan.get("analysis_methods", ["descriptive_stats", "text_analysis"])

        # Build analysis plan
        analysis_plan = {
            "name": f"Analysis for {self.project.name}",
            "dataset": "data/processed/dataset.json",
            "steps": [],
        }

        # Add text analysis on content
        if "text_analysis" in methods or True:  # Always run text analysis
            analysis_plan["steps"].append({
                "method": "text_analysis",
                "column": "content",
                "top_n": 30,
                "output": "text_analysis",
            })

        if "tfidf" in methods:
            analysis_plan["steps"].append({
                "method": "tfidf",
                "column": "content",
                "top_n": 20,
                "output": "tfidf_analysis",
            })

        if "descriptive_stats" in methods:
            analysis_plan["steps"].append({
                "method": "descriptive_stats",
                "columns": ["quality_score"],
                "output": "quality_stats",
            })

        # Execute plan
        results = self.analysis_engine.execute_plan(analysis_plan)

        # Use AI to interpret results
        if self.ai_client:
            try:
                results_str = json.dumps(results, indent=2, default=str)[:3000]
                interpretation = self.ai_generate(
                    prompt=(
                        f"Analyze and interpret the following research data analysis results "
                        f"for the topic '{self.project.config.topic}':\n\n"
                        f"{results_str}\n\n"
                        f"Provide key findings and insights. Format as a bulleted list."
                    ),
                    task="interpret_analysis",
                )
                results["ai_interpretation"] = interpretation
            except Exception as e:
                self.logger.warning("AI interpretation failed: %s", e)

        self.state.memory.add_finding(
            f"Analysis complete: {len(analysis_plan['steps'])} methods executed",
            source="analysis",
        )
        self.state.progress_pct = 60.0
        self.save_state()
        self.logger.info("Analysis complete")
        return results

    def draft(self) -> dict[str, Any]:
        """Draft the whitepaper report."""
        self.logger.info("Starting report drafting")
        self.state.current_task = "drafting"

        # Create report
        report = self.report_composer.create_report(
            self.project.name,
            title=f"Research Report: {self.project.config.topic}",
        )

        # Build context for drafting
        data_summary = self.data_store.get_summary()
        analysis_results = {}
        results_path = self.project.path / "analysis" / "outputs" / "results_summary.json"
        if results_path.exists():
            from shared.utils.files import load_json
            analysis_results = load_json(results_path)

        context = {
            "research_questions": self.project.config.research_questions,
            "data_summary": json.dumps(data_summary, indent=2),
            "analysis_results": json.dumps(analysis_results, indent=2, default=str)[:5000],
            "key_findings": [f["finding"] for f in self.state.memory.findings],
        }

        # Draft all sections
        report = self.report_composer.draft_all_sections(report, context)

        # Save draft
        draft_dir = self.report_composer.save_draft(report)

        # Run quality checks
        quality_report = self.quality_checker.check(report)
        self.quality_checker.save_report(quality_report, draft_dir)

        self.state.progress_pct = 85.0
        self.save_state()

        result = {
            "title": report.title,
            "word_count": report.total_word_count,
            "sections": len(report.sections),
            "quality_score": quality_report.overall_score,
            "quality_recommendation": quality_report.recommendation,
            "draft_version": report.version,
        }

        self.logger.info(
            "Draft complete: %d words, quality score %.2f",
            report.total_word_count, quality_report.overall_score,
        )
        return result

    def submit(self) -> dict[str, Any]:
        """Submit the report for human review."""
        self.logger.info("Submitting report for review")
        self.state.current_task = "submission"
        self.state.progress_pct = 95.0

        result = {
            "project": self.project.name,
            "status": "submitted_for_review",
            "message": f"Report for '{self.project.config.topic}' is ready for review. "
                       f"Draft available at: {self.project.report_dir / 'drafts'}",
        }

        self.save_state()
        return result

    def revise(self, feedback: str) -> dict[str, Any]:
        """Revise the report based on reviewer feedback."""
        self.logger.info("Starting revision based on feedback")
        self.state.current_task = "revision"

        # Load current report
        latest_draft = self._find_latest_draft()
        if not latest_draft:
            return {"error": "No draft found to revise"}

        from shared.utils.files import load_json
        from shared.models.report import Report
        meta = load_json(latest_draft / "report_meta.json")
        report = Report.from_dict(meta)
        report.version += 1

        # Use AI to determine which sections need revision
        if self.ai_client:
            try:
                revision_plan = self.ai_generate(
                    prompt=(
                        f"Given this feedback on a research report:\n\n{feedback}\n\n"
                        f"Which sections need revision? List the section names "
                        f"(abstract, introduction, methodology, results, discussion, conclusion) "
                        f"and what changes are needed for each."
                    ),
                    task="revision_planning",
                )
                self.state.memory.iteration_history.append({
                    "version": report.version,
                    "feedback": feedback,
                    "revision_plan": revision_plan,
                })
            except Exception:
                pass

        # Revise sections based on feedback
        for section in report.sections:
            if section.name in ("references", "title_page", "appendices"):
                continue
            self.report_composer.revise_section(report, section.name, feedback)

        # Save new draft
        draft_dir = self.report_composer.save_draft(report)

        # Re-run quality checks
        quality_report = self.quality_checker.check(report)
        self.quality_checker.save_report(quality_report, draft_dir)

        self.save_state()

        return {
            "new_version": report.version,
            "quality_score": quality_report.overall_score,
            "recommendation": quality_report.recommendation,
        }

    # --- Helpers ---

    def _default_plan(self) -> dict:
        """Generate a default research plan when AI is unavailable."""
        topic = self.project.config.topic
        return {
            "search_queries": [
                topic,
                f"{topic} research",
                f"{topic} data analysis",
                f"{topic} trends",
                f"{topic} statistics",
            ],
            "data_targets": ["academic papers", "datasets", "news articles"],
            "analysis_methods": ["descriptive_stats", "text_analysis", "trend_detection"],
            "report_outline": [
                "Introduction to the topic",
                "Literature review",
                "Data collection methodology",
                "Key findings and analysis",
                "Discussion of implications",
                "Conclusions and future work",
            ],
        }

    def _find_latest_draft(self) -> Path | None:
        """Find the latest draft version directory."""
        drafts_dir = self.project.path / "report" / "drafts"
        if not drafts_dir.exists():
            return None
        versions = sorted(drafts_dir.iterdir(), reverse=True)
        return versions[0] if versions else None
