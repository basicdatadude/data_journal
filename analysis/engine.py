"""Analysis engine: orchestrates analysis plans and produces results."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from analysis.patterns.detector import (
    AnomalyDetector,
    CorrelationAnalyzer,
    TextAnalyzer,
    TrendDetector,
)
from analysis.statistics.descriptive import (
    ComparisonResult,
    DescriptiveStats,
    RegressionResult,
    cohens_d,
    compute_descriptive,
    linear_regression,
    t_test,
)
from shared.utils.files import load_json, load_yaml, save_json, save_yaml
from shared.utils.logging import get_logger

logger = get_logger("analysis")


class AnalysisEngine:
    """Execute analysis plans and produce results for research projects."""

    # Registry of analysis methods
    METHODS = {
        "descriptive_stats",
        "trend_detection",
        "correlation",
        "regression",
        "anomaly_detection",
        "text_analysis",
        "tfidf",
        "comparison",
    }

    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.analysis_dir = project_path / "analysis"
        self.outputs_dir = self.analysis_dir / "outputs"
        self.figures_dir = self.outputs_dir / "figures"
        self._log_path = self.outputs_dir / "analysis_log.jsonl"

    def execute_plan(self, plan: dict) -> dict[str, Any]:
        """Execute an analysis plan and return all results.

        The plan should have the structure:
        {
            "name": "Analysis Plan Name",
            "dataset": "path/to/dataset.json",
            "steps": [
                {"method": "descriptive_stats", "columns": [...], "output": "..."},
                ...
            ]
        }
        """
        self.outputs_dir.mkdir(parents=True, exist_ok=True)
        self.figures_dir.mkdir(parents=True, exist_ok=True)

        plan_name = plan.get("name", "unnamed")
        dataset_path = plan.get("dataset", "")
        steps = plan.get("steps", [])

        logger.info("Executing analysis plan: %s (%d steps)", plan_name, len(steps))

        # Load dataset
        data = self._load_dataset(dataset_path)
        results: dict[str, Any] = {}

        for i, step in enumerate(steps):
            method = step.get("method", "")
            output_name = step.get("output", f"step_{i}")

            logger.info("Running step %d/%d: %s", i + 1, len(steps), method)
            self._log_event("step_start", method=method, step=i)

            try:
                result = self._run_method(method, step, data)
                results[output_name] = result

                # Save step output
                output_path = self.outputs_dir / f"{output_name}.json"
                save_json(output_path, result)

                self._log_event("step_complete", method=method, step=i)
            except Exception as e:
                logger.error("Step %d (%s) failed: %s", i, method, e)
                results[output_name] = {"error": str(e)}
                self._log_event("step_error", method=method, step=i, error=str(e))

        # Save the plan alongside results
        save_yaml(self.analysis_dir / "plan.yaml", plan)

        # Save combined results summary
        save_json(self.outputs_dir / "results_summary.json", {
            "plan_name": plan_name,
            "steps_completed": len([r for r in results.values() if "error" not in r]),
            "steps_failed": len([r for r in results.values() if "error" in r]),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "results": results,
        })

        return results

    def _load_dataset(self, path_str: str) -> list[dict]:
        """Load dataset from the project directory."""
        if not path_str:
            # Default to processed dataset
            path = self.project_path / "data" / "processed" / "dataset.json"
        else:
            path = self.project_path / path_str

        if not path.exists():
            logger.warning("Dataset not found: %s", path)
            return []

        data = load_json(path)
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "records" in data:
            return data["records"]
        return [data]

    def _run_method(self, method: str, step: dict, data: list[dict]) -> dict:
        """Dispatch to the appropriate analysis method."""
        if method == "descriptive_stats":
            return self._descriptive_stats(step, data)
        elif method == "trend_detection":
            return self._trend_detection(step, data)
        elif method == "correlation":
            return self._correlation(step, data)
        elif method == "regression":
            return self._regression(step, data)
        elif method == "anomaly_detection":
            return self._anomaly_detection(step, data)
        elif method == "text_analysis":
            return self._text_analysis(step, data)
        elif method == "tfidf":
            return self._tfidf(step, data)
        elif method == "comparison":
            return self._comparison(step, data)
        else:
            raise ValueError(f"Unknown analysis method: {method}")

    def _extract_column(self, data: list[dict], column: str) -> list[float]:
        """Extract numeric values from a column in the dataset."""
        values = []
        for record in data:
            val = record.get(column)
            if val is not None:
                try:
                    values.append(float(val))
                except (ValueError, TypeError):
                    continue
        return values

    def _extract_text_column(self, data: list[dict], column: str) -> list[str]:
        """Extract text values from a column."""
        return [str(record.get(column, "")) for record in data if record.get(column)]

    def _descriptive_stats(self, step: dict, data: list[dict]) -> dict:
        columns = step.get("columns", [])
        results = {}
        for col in columns:
            values = self._extract_column(data, col)
            stats = compute_descriptive(values, name=col)
            results[col] = stats.to_dict()
        return {"method": "descriptive_stats", "results": results}

    def _trend_detection(self, step: dict, data: list[dict]) -> dict:
        column = step.get("column", "")
        values = self._extract_column(data, column)
        labels = self._extract_text_column(data, step.get("time_column", ""))

        trend = TrendDetector.detect(values, labels or None)
        moving_avg = TrendDetector.moving_average(values, step.get("window", 3))

        return {
            "method": "trend_detection",
            "column": column,
            "trend": trend.to_dict(),
            "moving_average": moving_avg,
            "data_points": len(values),
        }

    def _correlation(self, step: dict, data: list[dict]) -> dict:
        columns = step.get("columns", [])
        col_data = {col: self._extract_column(data, col) for col in columns}
        matrix = CorrelationAnalyzer.correlation_matrix(col_data)

        results = {}
        for (vx, vy), result in matrix.items():
            results[f"{vx}_vs_{vy}"] = result.to_dict()

        return {"method": "correlation", "matrix": results}

    def _regression(self, step: dict, data: list[dict]) -> dict:
        dependent = step.get("dependent", "")
        independent = step.get("independent", [])

        y = self._extract_column(data, dependent)
        results = {}

        for ind_var in independent:
            x = self._extract_column(data, ind_var)
            reg = linear_regression(x, y, x_name=ind_var, y_name=dependent)
            results[ind_var] = reg.to_dict()

        return {"method": "regression", "dependent": dependent, "results": results}

    def _anomaly_detection(self, step: dict, data: list[dict]) -> dict:
        column = step.get("column", "")
        method = step.get("detection_method", "z_score")
        threshold = step.get("threshold", 2.0)
        values = self._extract_column(data, column)

        if method == "iqr":
            anomalies = AnomalyDetector.iqr_detect(values, multiplier=threshold)
        else:
            anomalies = AnomalyDetector.z_score_detect(values, threshold=threshold)

        flagged = [a.to_dict() for a in anomalies if a.is_anomaly]
        return {
            "method": "anomaly_detection",
            "column": column,
            "detection_method": method,
            "total_points": len(values),
            "anomalies_found": len(flagged),
            "anomalies": flagged,
        }

    def _text_analysis(self, step: dict, data: list[dict]) -> dict:
        column = step.get("column", "content")
        top_n = step.get("top_n", 20)
        texts = self._extract_text_column(data, column)

        result = TextAnalyzer.analyze(texts, top_n=top_n)
        return {"method": "text_analysis", **result.to_dict()}

    def _tfidf(self, step: dict, data: list[dict]) -> dict:
        column = step.get("column", "content")
        top_n = step.get("top_n", 20)
        texts = self._extract_text_column(data, column)

        scores = TextAnalyzer.tfidf(texts, top_n=top_n)
        return {
            "method": "tfidf",
            "top_terms": [{"term": t, "score": round(s, 6)} for t, s in scores],
            "document_count": len(texts),
        }

    def _comparison(self, step: dict, data: list[dict]) -> dict:
        column = step.get("column", "")
        group_by = step.get("group_by", "")

        groups: dict[str, list[float]] = {}
        for record in data:
            group = str(record.get(group_by, "unknown"))
            val = record.get(column)
            if val is not None:
                try:
                    groups.setdefault(group, []).append(float(val))
                except (ValueError, TypeError):
                    continue

        group_names = list(groups.keys())
        results = {}

        # Pairwise t-tests
        for i, g1 in enumerate(group_names):
            for j, g2 in enumerate(group_names):
                if j <= i:
                    continue
                comp = t_test(groups[g1], groups[g2])
                comp.test_name = f"{g1}_vs_{g2}"
                results[comp.test_name] = comp.to_dict()

        # Descriptive stats per group
        group_stats = {}
        for name, vals in groups.items():
            group_stats[name] = compute_descriptive(vals, name=name).to_dict()

        return {
            "method": "comparison",
            "column": column,
            "group_by": group_by,
            "group_stats": group_stats,
            "comparisons": results,
        }

    def _log_event(self, event: str, **data):
        from shared.utils.files import append_jsonl
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event": event,
            **data,
        }
        append_jsonl(self._log_path, entry)
