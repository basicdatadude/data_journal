"""Descriptive statistics and comparative analysis."""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from typing import Any


@dataclass
class DescriptiveStats:
    """Summary statistics for a numeric variable."""
    variable_name: str = ""
    count: int = 0
    mean: float = 0.0
    median: float = 0.0
    mode: float | None = None
    std_dev: float = 0.0
    variance: float = 0.0
    min_val: float = 0.0
    max_val: float = 0.0
    range_val: float = 0.0
    q1: float = 0.0
    q3: float = 0.0
    iqr: float = 0.0
    skewness: float = 0.0

    def to_dict(self) -> dict:
        return {
            "variable": self.variable_name,
            "count": self.count,
            "mean": round(self.mean, 4),
            "median": round(self.median, 4),
            "mode": round(self.mode, 4) if self.mode is not None else None,
            "std_dev": round(self.std_dev, 4),
            "variance": round(self.variance, 4),
            "min": round(self.min_val, 4),
            "max": round(self.max_val, 4),
            "range": round(self.range_val, 4),
            "q1": round(self.q1, 4),
            "q3": round(self.q3, 4),
            "iqr": round(self.iqr, 4),
            "skewness": round(self.skewness, 4),
        }


@dataclass
class RegressionResult:
    """Result of a linear regression analysis."""
    dependent: str = ""
    independent: list[str] = field(default_factory=list)
    coefficients: dict[str, float] = field(default_factory=dict)
    intercept: float = 0.0
    r_squared: float = 0.0
    adjusted_r_squared: float = 0.0
    residuals: list[float] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "dependent": self.dependent,
            "independent": self.independent,
            "coefficients": {k: round(v, 6) for k, v in self.coefficients.items()},
            "intercept": round(self.intercept, 6),
            "r_squared": round(self.r_squared, 4),
            "adjusted_r_squared": round(self.adjusted_r_squared, 4),
            "summary": self.summary,
        }

    def predict(self, values: dict[str, float]) -> float:
        """Predict the dependent variable given independent variable values."""
        result = self.intercept
        for var, coef in self.coefficients.items():
            result += coef * values.get(var, 0)
        return result


@dataclass
class ComparisonResult:
    """Result of a group comparison test."""
    test_name: str = ""
    statistic: float = 0.0
    p_value: float = 0.0
    effect_size: float = 0.0
    significant: bool = False
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "test_name": self.test_name,
            "statistic": round(self.statistic, 4),
            "p_value": round(self.p_value, 6),
            "effect_size": round(self.effect_size, 4),
            "significant": self.significant,
            "summary": self.summary,
        }


def compute_descriptive(values: list[float], name: str = "") -> DescriptiveStats:
    """Compute descriptive statistics for a list of values."""
    if not values:
        return DescriptiveStats(variable_name=name)

    n = len(values)
    sorted_vals = sorted(values)
    mean = statistics.mean(values)
    median = statistics.median(values)

    try:
        mode = statistics.mode(values)
    except statistics.StatisticsError:
        mode = None

    stdev = statistics.stdev(values) if n > 1 else 0.0
    var = statistics.variance(values) if n > 1 else 0.0

    q1 = sorted_vals[n // 4] if n >= 4 else sorted_vals[0]
    q3 = sorted_vals[3 * n // 4] if n >= 4 else sorted_vals[-1]

    # Skewness (Fisher's method)
    skewness = 0.0
    if n > 2 and stdev > 0:
        skewness = (n / ((n - 1) * (n - 2))) * sum(((x - mean) / stdev) ** 3 for x in values)

    return DescriptiveStats(
        variable_name=name,
        count=n,
        mean=mean,
        median=median,
        mode=mode,
        std_dev=stdev,
        variance=var,
        min_val=min(values),
        max_val=max(values),
        range_val=max(values) - min(values),
        q1=q1,
        q3=q3,
        iqr=q3 - q1,
        skewness=skewness,
    )


def linear_regression(
    x: list[float],
    y: list[float],
    x_name: str = "x",
    y_name: str = "y",
) -> RegressionResult:
    """Simple linear regression (single independent variable)."""
    n = min(len(x), len(y))
    if n < 2:
        return RegressionResult(summary="Insufficient data for regression")

    x = x[:n]
    y = y[:n]
    x_mean = statistics.mean(x)
    y_mean = statistics.mean(y)

    ss_xy = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, y))
    ss_xx = sum((xi - x_mean) ** 2 for xi in x)

    if ss_xx == 0:
        return RegressionResult(summary="No variance in independent variable")

    slope = ss_xy / ss_xx
    intercept = y_mean - slope * x_mean

    predicted = [slope * xi + intercept for xi in x]
    residuals = [yi - pi for yi, pi in zip(y, predicted)]

    ss_res = sum(r ** 2 for r in residuals)
    ss_tot = sum((yi - y_mean) ** 2 for yi in y)
    r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
    adj_r_squared = 1 - ((1 - r_squared) * (n - 1) / (n - 2)) if n > 2 else r_squared

    return RegressionResult(
        dependent=y_name,
        independent=[x_name],
        coefficients={x_name: slope},
        intercept=intercept,
        r_squared=r_squared,
        adjusted_r_squared=adj_r_squared,
        residuals=residuals,
        summary=f"y = {slope:.4f}*{x_name} + {intercept:.4f} "
                f"(R²={r_squared:.4f}, adj R²={adj_r_squared:.4f})",
    )


def cohens_d(group1: list[float], group2: list[float]) -> float:
    """Compute Cohen's d effect size for two groups."""
    n1, n2 = len(group1), len(group2)
    if n1 < 2 or n2 < 2:
        return 0.0

    mean1 = statistics.mean(group1)
    mean2 = statistics.mean(group2)
    var1 = statistics.variance(group1)
    var2 = statistics.variance(group2)

    pooled_std = math.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2))
    if pooled_std == 0:
        return 0.0
    return (mean1 - mean2) / pooled_std


def t_test(group1: list[float], group2: list[float], alpha: float = 0.05) -> ComparisonResult:
    """Independent samples t-test (Welch's t-test approximation)."""
    n1, n2 = len(group1), len(group2)
    if n1 < 2 or n2 < 2:
        return ComparisonResult(test_name="t-test", summary="Insufficient data")

    mean1 = statistics.mean(group1)
    mean2 = statistics.mean(group2)
    var1 = statistics.variance(group1)
    var2 = statistics.variance(group2)

    se = math.sqrt(var1 / n1 + var2 / n2)
    if se == 0:
        return ComparisonResult(test_name="t-test", summary="No variance in groups")

    t_stat = (mean1 - mean2) / se

    # Welch-Satterthwaite degrees of freedom
    num = (var1 / n1 + var2 / n2) ** 2
    denom = (var1 / n1) ** 2 / (n1 - 1) + (var2 / n2) ** 2 / (n2 - 1)
    df = num / denom if denom > 0 else n1 + n2 - 2

    # Approximate p-value using normal distribution for large df
    # For a proper implementation, use scipy.stats.t.sf
    z = abs(t_stat)
    p_value = 2 * (1 - _normal_cdf(z))

    effect = cohens_d(group1, group2)
    significant = p_value < alpha

    return ComparisonResult(
        test_name="welch_t_test",
        statistic=t_stat,
        p_value=p_value,
        effect_size=effect,
        significant=significant,
        summary=f"t({df:.1f}) = {t_stat:.4f}, p = {p_value:.6f}, d = {effect:.4f}. "
                f"{'Significant' if significant else 'Not significant'} at α={alpha}",
    )


def _normal_cdf(x: float) -> float:
    """Approximate CDF of the standard normal distribution."""
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))
