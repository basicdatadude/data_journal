# Skill: Quality Assurance

## Purpose

Ensure that all outputs — data, analyses, and reports — meet academic standards of rigor, accuracy, and completeness before human review.

## Quality Domains

### Data Quality
- **Completeness**: Are all expected data fields populated?
- **Accuracy**: Do values pass validation and cross-reference checks?
- **Timeliness**: Is the data current enough for the research questions?
- **Consistency**: Do multiple sources agree on the same facts?
- **Provenance**: Is every data point traceable to its source?

### Analysis Quality
- **Reproducibility**: Can the analysis be re-run with the same results?
- **Methodology**: Are the chosen methods appropriate for the data and questions?
- **Statistical rigor**: Are assumptions checked, tests applied correctly, effect sizes reported?
- **Visualization**: Are charts accurate, labeled, and publication-ready?
- **Documentation**: Is the analysis process fully documented?

### Report Quality
- **Structure**: Does the paper follow the required template and section ordering?
- **Content**: Are all claims supported by evidence or citations?
- **Citations**: Are all references complete, properly formatted, and resolvable?
- **Writing**: Is the language academic, clear, and grammatically correct?
- **Figures/Tables**: Are all visual elements referenced, captioned, and accurate?
- **Originality**: Is the work original and properly attributed?

## Automated Checks

### Pre-submission Checks (run before human review)

```yaml
checks:
  - name: section_completeness
    description: All required sections present and non-empty
    severity: error

  - name: citation_integrity
    description: All inline citations have matching references
    severity: error

  - name: figure_references
    description: All figures/tables referenced in text
    severity: warning

  - name: minimum_length
    description: Abstract >= 150 words, body >= 3000 words
    severity: error

  - name: readability_score
    description: Flesch-Kincaid grade level between 12-16
    severity: warning

  - name: statistical_reporting
    description: Statistical claims include test name, p-value, effect size
    severity: warning

  - name: methodology_present
    description: Methodology section describes data collection and analysis methods
    severity: error

  - name: no_unsupported_claims
    description: AI-assisted check for claims lacking evidence
    severity: warning

  - name: consistent_terminology
    description: Key terms used consistently throughout
    severity: info
```

### Quality Report Format

```yaml
quality_report:
  project: "market-trends-2026"
  version: "v1"
  timestamp: "2026-02-21T16:00:00Z"
  overall_score: 0.82  # 0.0 to 1.0

  checks:
    - name: section_completeness
      passed: true
      details: "All 10 required sections present"

    - name: citation_integrity
      passed: false
      details: "2 inline citations missing from references: [Smith2024], [Jones2025]"

    - name: minimum_length
      passed: true
      details: "Abstract: 245 words, Body: 4,832 words"

  summary:
    errors: 1
    warnings: 2
    info: 1

  recommendation: "fix_errors"  # ready | fix_errors | fix_warnings | major_revision
```

## Human Review Checklist

When a report is submitted for human review, present this checklist:

- [ ] Research questions are clearly stated and addressed
- [ ] Methodology is appropriate and well-described
- [ ] Data sources are credible and sufficient
- [ ] Analysis is sound and conclusions follow from evidence
- [ ] Report is well-written and properly formatted
- [ ] All claims are supported by data or citations
- [ ] Figures and tables add value and are accurate
- [ ] The report provides novel insight or useful synthesis
- [ ] The report is ready for external distribution

## Continuous Improvement

Track quality metrics across projects to identify systemic issues:
- Average quality score at first submission
- Most common check failures
- Average number of revision cycles
- Quality score improvement between versions
