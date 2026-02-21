"""Pattern detection: trend detection, correlation, anomaly detection, and text analysis."""

from __future__ import annotations

import math
import statistics
from collections import Counter
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TrendResult:
    direction: str  # "increasing", "decreasing", "stable"
    slope: float = 0.0
    r_squared: float = 0.0
    change_points: list[int] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "direction": self.direction,
            "slope": round(self.slope, 6),
            "r_squared": round(self.r_squared, 4),
            "change_points": self.change_points,
            "summary": self.summary,
        }


@dataclass
class CorrelationResult:
    variable_x: str
    variable_y: str
    pearson_r: float = 0.0
    strength: str = ""  # "strong", "moderate", "weak", "none"
    direction: str = ""  # "positive", "negative"
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "variable_x": self.variable_x,
            "variable_y": self.variable_y,
            "pearson_r": round(self.pearson_r, 4),
            "strength": self.strength,
            "direction": self.direction,
            "summary": self.summary,
        }


@dataclass
class AnomalyResult:
    index: int
    value: float
    z_score: float
    is_anomaly: bool

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "value": self.value,
            "z_score": round(self.z_score, 4),
            "is_anomaly": self.is_anomaly,
        }


@dataclass
class TextAnalysisResult:
    top_terms: list[tuple[str, int]] = field(default_factory=list)
    term_frequencies: dict[str, int] = field(default_factory=dict)
    document_count: int = 0
    avg_length: float = 0.0
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "top_terms": [{"term": t, "count": c} for t, c in self.top_terms],
            "document_count": self.document_count,
            "avg_length": round(self.avg_length, 1),
            "summary": self.summary,
        }


class TrendDetector:
    """Detect trends in numeric time-series data."""

    @staticmethod
    def detect(values: list[float], labels: list[str] | None = None) -> TrendResult:
        """Detect trend using simple linear regression."""
        n = len(values)
        if n < 2:
            return TrendResult(direction="insufficient_data", summary="Need at least 2 data points")

        x = list(range(n))
        x_mean = statistics.mean(x)
        y_mean = statistics.mean(values)

        numerator = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, values))
        denominator = sum((xi - x_mean) ** 2 for xi in x)

        if denominator == 0:
            return TrendResult(direction="stable", slope=0.0, summary="No variation in time index")

        slope = numerator / denominator
        intercept = y_mean - slope * x_mean

        # R-squared
        predicted = [slope * xi + intercept for xi in x]
        ss_res = sum((yi - pi) ** 2 for yi, pi in zip(values, predicted))
        ss_tot = sum((yi - y_mean) ** 2 for yi in values)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        # Change point detection (simple: where sign of derivative changes)
        change_points = []
        for i in range(1, n - 1):
            if (values[i] - values[i - 1]) * (values[i + 1] - values[i]) < 0:
                change_points.append(i)

        if abs(slope) < 0.01:
            direction = "stable"
        elif slope > 0:
            direction = "increasing"
        else:
            direction = "decreasing"

        return TrendResult(
            direction=direction,
            slope=slope,
            r_squared=r_squared,
            change_points=change_points,
            summary=f"Trend is {direction} with slope {slope:.4f} (R²={r_squared:.3f}), "
                    f"{len(change_points)} change points detected",
        )

    @staticmethod
    def moving_average(values: list[float], window: int = 3) -> list[float]:
        """Compute a simple moving average."""
        if len(values) < window:
            return values[:]
        result = []
        for i in range(len(values) - window + 1):
            avg = statistics.mean(values[i:i + window])
            result.append(round(avg, 4))
        return result


class CorrelationAnalyzer:
    """Compute correlations between numeric variables."""

    @staticmethod
    def pearson(x: list[float], y: list[float]) -> CorrelationResult:
        """Compute Pearson correlation coefficient."""
        n = min(len(x), len(y))
        if n < 2:
            return CorrelationResult("x", "y", summary="Insufficient data")

        x = x[:n]
        y = y[:n]
        x_mean = statistics.mean(x)
        y_mean = statistics.mean(y)

        numerator = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, y))
        denom_x = math.sqrt(sum((xi - x_mean) ** 2 for xi in x))
        denom_y = math.sqrt(sum((yi - y_mean) ** 2 for yi in y))

        if denom_x == 0 or denom_y == 0:
            return CorrelationResult("x", "y", pearson_r=0.0, strength="none",
                                     summary="No variation in one or both variables")

        r = numerator / (denom_x * denom_y)
        r = max(-1.0, min(1.0, r))

        abs_r = abs(r)
        if abs_r >= 0.7:
            strength = "strong"
        elif abs_r >= 0.4:
            strength = "moderate"
        elif abs_r >= 0.2:
            strength = "weak"
        else:
            strength = "none"

        direction = "positive" if r > 0 else "negative" if r < 0 else "none"

        return CorrelationResult(
            variable_x="x",
            variable_y="y",
            pearson_r=r,
            strength=strength,
            direction=direction,
            summary=f"{strength.title()} {direction} correlation (r={r:.4f})",
        )

    @staticmethod
    def correlation_matrix(
        data: dict[str, list[float]],
    ) -> dict[tuple[str, str], CorrelationResult]:
        """Compute pairwise correlations for multiple variables."""
        variables = list(data.keys())
        results: dict[tuple[str, str], CorrelationResult] = {}

        for i, var_x in enumerate(variables):
            for j, var_y in enumerate(variables):
                if j <= i:
                    continue
                result = CorrelationAnalyzer.pearson(data[var_x], data[var_y])
                result.variable_x = var_x
                result.variable_y = var_y
                results[(var_x, var_y)] = result

        return results


class AnomalyDetector:
    """Detect anomalies using statistical methods."""

    @staticmethod
    def z_score_detect(values: list[float], threshold: float = 2.0) -> list[AnomalyResult]:
        """Detect anomalies using Z-score method."""
        if len(values) < 3:
            return []

        mean = statistics.mean(values)
        stdev = statistics.stdev(values)
        if stdev == 0:
            return []

        results = []
        for i, v in enumerate(values):
            z = (v - mean) / stdev
            results.append(AnomalyResult(
                index=i,
                value=v,
                z_score=z,
                is_anomaly=abs(z) > threshold,
            ))
        return results

    @staticmethod
    def iqr_detect(values: list[float], multiplier: float = 1.5) -> list[AnomalyResult]:
        """Detect anomalies using IQR method."""
        if len(values) < 4:
            return []

        sorted_vals = sorted(values)
        n = len(sorted_vals)
        q1 = sorted_vals[n // 4]
        q3 = sorted_vals[3 * n // 4]
        iqr = q3 - q1
        lower = q1 - multiplier * iqr
        upper = q3 + multiplier * iqr

        mean = statistics.mean(values)
        stdev = statistics.stdev(values) if len(values) > 1 else 1.0

        results = []
        for i, v in enumerate(values):
            z = (v - mean) / stdev if stdev > 0 else 0
            results.append(AnomalyResult(
                index=i,
                value=v,
                z_score=z,
                is_anomaly=v < lower or v > upper,
            ))
        return results


class TextAnalyzer:
    """Basic text analysis: term frequency, keyword extraction."""

    STOP_WORDS = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "is", "was", "are", "were", "be", "been",
        "being", "have", "has", "had", "do", "does", "did", "will", "would",
        "could", "should", "may", "might", "can", "shall", "this", "that",
        "these", "those", "it", "its", "not", "no", "as", "if", "then",
        "than", "so", "up", "out", "about", "into", "over", "after",
    }

    @classmethod
    def analyze(cls, documents: list[str], top_n: int = 20) -> TextAnalysisResult:
        """Analyze a collection of text documents."""
        if not documents:
            return TextAnalysisResult(summary="No documents to analyze")

        all_words: list[str] = []
        total_length = 0

        for doc in documents:
            words = cls._tokenize(doc)
            all_words.extend(words)
            total_length += len(doc)

        # Term frequencies (excluding stop words)
        freq = Counter(w for w in all_words if w not in cls.STOP_WORDS and len(w) > 2)
        top_terms = freq.most_common(top_n)

        avg_length = total_length / len(documents)

        return TextAnalysisResult(
            top_terms=top_terms,
            term_frequencies=dict(freq),
            document_count=len(documents),
            avg_length=avg_length,
            summary=f"Analyzed {len(documents)} documents, {len(freq)} unique terms, "
                    f"avg length {avg_length:.0f} chars. "
                    f"Top terms: {', '.join(t for t, _ in top_terms[:5])}",
        )

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Simple word tokenization."""
        import re
        return re.findall(r"\b[a-zA-Z]+\b", text.lower())

    @classmethod
    def tfidf(cls, documents: list[str], top_n: int = 20) -> list[tuple[str, float]]:
        """Compute TF-IDF scores across documents."""
        if not documents:
            return []

        doc_words = [cls._tokenize(doc) for doc in documents]
        n_docs = len(documents)

        # Document frequency
        df: Counter = Counter()
        for words in doc_words:
            unique = set(w for w in words if w not in cls.STOP_WORDS and len(w) > 2)
            df.update(unique)

        # TF-IDF for all docs combined
        all_words = [w for words in doc_words for w in words
                     if w not in cls.STOP_WORDS and len(w) > 2]
        tf = Counter(all_words)
        total = len(all_words) or 1

        scores = {}
        for term, count in tf.items():
            term_tf = count / total
            term_idf = math.log(n_docs / (1 + df.get(term, 0)))
            scores[term] = term_tf * term_idf

        return sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_n]
