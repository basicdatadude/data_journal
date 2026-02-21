"""Tests for the analysis engine."""

import pytest
from analysis.patterns.detector import (
    TrendDetector,
    CorrelationAnalyzer,
    AnomalyDetector,
    TextAnalyzer,
)
from analysis.statistics.descriptive import (
    compute_descriptive,
    linear_regression,
    t_test,
    cohens_d,
)


class TestTrendDetector:
    def test_increasing_trend(self):
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        result = TrendDetector.detect(values)
        assert result.direction == "increasing"
        assert result.slope > 0

    def test_decreasing_trend(self):
        values = [5.0, 4.0, 3.0, 2.0, 1.0]
        result = TrendDetector.detect(values)
        assert result.direction == "decreasing"
        assert result.slope < 0

    def test_stable_trend(self):
        values = [3.0, 3.0, 3.0, 3.0, 3.0]
        result = TrendDetector.detect(values)
        assert result.direction == "stable"

    def test_moving_average(self):
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        result = TrendDetector.moving_average(values, window=3)
        assert len(result) == 3
        assert result[0] == pytest.approx(2.0)

    def test_insufficient_data(self):
        result = TrendDetector.detect([1.0])
        assert result.direction == "insufficient_data"


class TestCorrelationAnalyzer:
    def test_perfect_positive(self):
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        y = [2.0, 4.0, 6.0, 8.0, 10.0]
        result = CorrelationAnalyzer.pearson(x, y)
        assert result.pearson_r == pytest.approx(1.0, abs=0.001)
        assert result.strength == "strong"
        assert result.direction == "positive"

    def test_perfect_negative(self):
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        y = [10.0, 8.0, 6.0, 4.0, 2.0]
        result = CorrelationAnalyzer.pearson(x, y)
        assert result.pearson_r == pytest.approx(-1.0, abs=0.001)
        assert result.direction == "negative"

    def test_correlation_matrix(self):
        data = {
            "a": [1.0, 2.0, 3.0],
            "b": [2.0, 4.0, 6.0],
            "c": [3.0, 1.0, 2.0],
        }
        matrix = CorrelationAnalyzer.correlation_matrix(data)
        assert ("a", "b") in matrix
        assert ("a", "c") in matrix


class TestAnomalyDetector:
    def test_z_score_detects_outlier(self):
        values = [1.0, 1.1, 0.9, 1.0, 1.1, 0.9, 1.0, 10.0]  # 10.0 is anomaly
        results = AnomalyDetector.z_score_detect(values, threshold=2.0)
        anomalies = [r for r in results if r.is_anomaly]
        assert len(anomalies) >= 1
        assert any(r.value == 10.0 for r in anomalies)

    def test_iqr_detects_outlier(self):
        values = [1.0, 1.1, 0.9, 1.0, 1.1, 0.9, 1.0, 10.0]
        results = AnomalyDetector.iqr_detect(values, multiplier=1.5)
        anomalies = [r for r in results if r.is_anomaly]
        assert len(anomalies) >= 1


class TestTextAnalyzer:
    def test_analyze_documents(self):
        docs = [
            "Python is a popular programming language",
            "Python is used for data science and machine learning",
            "Data science requires knowledge of statistics and programming",
        ]
        result = TextAnalyzer.analyze(docs)
        assert result.document_count == 3
        assert result.avg_length > 0
        assert len(result.top_terms) > 0

    def test_tfidf(self):
        docs = [
            "The cat sat on the mat",
            "The dog played in the park",
            "The cat and the dog are friends",
        ]
        scores = TextAnalyzer.tfidf(docs, top_n=5)
        assert len(scores) > 0
        assert all(isinstance(s, tuple) and len(s) == 2 for s in scores)


class TestDescriptiveStats:
    def test_basic_stats(self):
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        stats = compute_descriptive(values, "test")
        assert stats.count == 5
        assert stats.mean == pytest.approx(3.0)
        assert stats.median == pytest.approx(3.0)
        assert stats.min_val == 1.0
        assert stats.max_val == 5.0
        assert stats.range_val == 4.0

    def test_empty_data(self):
        stats = compute_descriptive([], "empty")
        assert stats.count == 0


class TestLinearRegression:
    def test_perfect_fit(self):
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        y = [2.0, 4.0, 6.0, 8.0, 10.0]  # y = 2x
        result = linear_regression(x, y)
        assert result.coefficients["x"] == pytest.approx(2.0, abs=0.01)
        assert result.r_squared == pytest.approx(1.0, abs=0.01)

    def test_prediction(self):
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        y = [2.0, 4.0, 6.0, 8.0, 10.0]
        result = linear_regression(x, y)
        pred = result.predict({"x": 6.0})
        assert pred == pytest.approx(12.0, abs=0.1)


class TestTTest:
    def test_different_groups(self):
        group1 = [10.0, 11.0, 12.0, 13.0, 14.0]
        group2 = [20.0, 21.0, 22.0, 23.0, 24.0]
        result = t_test(group1, group2)
        assert result.significant
        assert result.p_value < 0.05

    def test_similar_groups(self):
        group1 = [10.0, 10.1, 9.9, 10.0, 10.1]
        group2 = [10.0, 10.1, 9.9, 10.0, 10.1]
        result = t_test(group1, group2)
        assert not result.significant


class TestCohensD:
    def test_large_effect(self):
        group1 = [10.0, 11.0, 12.0, 13.0, 14.0]
        group2 = [20.0, 21.0, 22.0, 23.0, 24.0]
        d = cohens_d(group1, group2)
        assert abs(d) > 0.8  # Large effect
