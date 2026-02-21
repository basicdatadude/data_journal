# Skill: Analysis

## Purpose

Detect patterns, compute statistics, generate insights, and produce evidence for whitepapers. The analysis engine provides a toolkit of methods that research agents invoke against collected data.

## Analysis Methods

### Descriptive Statistics
- Central tendency: mean, median, mode
- Dispersion: standard deviation, variance, IQR, range
- Distribution: histograms, density plots, Q-Q plots
- Summary tables with key metrics

### Trend Detection
- Time-series decomposition (trend, seasonality, residual)
- Moving averages and exponential smoothing
- Change-point detection
- Growth rate calculation and forecasting

### Correlation Analysis
- Pearson, Spearman, and Kendall correlation matrices
- Scatter plots with regression lines
- Partial correlation (controlling for confounders)
- Cross-correlation for lagged relationships

### Regression Analysis
- Linear regression (single and multiple)
- Logistic regression for categorical outcomes
- Polynomial regression for non-linear relationships
- Model diagnostics: R², adjusted R², residual plots, VIF

### Anomaly Detection
- Statistical outlier detection (Z-score, IQR method)
- Isolation forests for multivariate anomalies
- Time-series anomaly detection (STL decomposition residuals)

### Text Analysis
- Topic modeling (LDA, NMF)
- Sentiment analysis
- Named entity recognition and extraction
- Keyword frequency and TF-IDF analysis
- Text clustering and similarity

### Comparative Analysis
- Group comparisons (t-tests, ANOVA, chi-square)
- Effect size calculations (Cohen's d, odds ratios)
- Before/after analysis
- Cross-sectional comparisons

## Analysis Plan Schema

Agents create analysis plans that the engine executes:

```yaml
analysis_plan:
  name: "Market Trends Analysis"
  dataset: "data/processed/dataset.csv"
  steps:
    - method: descriptive_stats
      columns: [revenue, growth_rate, market_share]
      output: outputs/descriptive_summary.json

    - method: trend_detection
      column: revenue
      time_column: date
      period: quarterly
      output: outputs/revenue_trend.json

    - method: correlation
      columns: [revenue, marketing_spend, customer_count]
      output: outputs/correlation_matrix.json

    - method: regression
      dependent: revenue
      independent: [marketing_spend, customer_count, quarter]
      output: outputs/regression_results.json
```

## Visualization

Every analysis method can produce visualizations:
- Charts saved as PNG and SVG in `analysis/outputs/`
- Interactive HTML charts when beneficial
- All charts include titles, axis labels, legends, and source annotations
- Publication-ready styling suitable for whitepaper inclusion

## Reproducibility

- Every analysis run is logged with parameters, input data hash, and output hash
- Random seeds are tracked and recorded
- Environment info (Python version, library versions) is captured
- Analysis scripts are saved alongside outputs for reproducibility

## Output Structure

```
analysis/
├── scripts/                  # Analysis code
│   ├── run_descriptive.py
│   ├── run_trends.py
│   └── run_correlations.py
├── notebooks/                # Exploratory analysis
│   └── exploration.ipynb
├── outputs/                  # Results
│   ├── descriptive_summary.json
│   ├── trend_results.json
│   ├── correlation_matrix.json
│   ├── figures/
│   │   ├── revenue_trend.png
│   │   ├── correlation_heatmap.png
│   │   └── distribution_plots.png
│   └── analysis_log.jsonl    # Execution log
└── plan.yaml                 # The analysis plan that was executed
```
