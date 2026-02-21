# Skill: Report Generation

## Purpose

Compose, format, and refine academic-quality whitepapers from analysis results, collected data, and AI-generated prose. Reports must meet publication standards for structure, citations, and rigor.

## Whitepaper Structure

Every report follows this standard academic structure:

1. **Title Page** — Title, author(s), date, abstract
2. **Abstract** — 150-300 word summary of the entire paper
3. **Introduction** — Context, problem statement, research questions, scope
4. **Literature Review** — Summary of existing work and how this research fits
5. **Methodology** — Data collection methods, analysis techniques, tools used
6. **Results** — Findings presented with tables, figures, and statistical evidence
7. **Discussion** — Interpretation of results, implications, limitations
8. **Conclusion** — Summary of key findings, recommendations, future work
9. **References** — Complete bibliography in APA or IEEE format
10. **Appendices** — Supporting data, additional tables, code references

## Composition Process

### Section-by-Section Drafting
- Each section is drafted independently using AI assistance
- The agent provides context: research questions, data summary, analysis results
- AI generates a draft respecting academic tone, structure, and evidence standards
- Sections are reviewed for internal consistency before assembly

### Citation Management
- All factual claims must be supported by citations
- Citations are tracked in `references/bibliography.yaml`
- Inline citations formatted per chosen style (APA default)
- Reference list auto-generated from cited sources
- Orphan citation detection (cited but not in references, or vice versa)

### Figure & Table Integration
- Figures pulled from `analysis/outputs/figures/`
- Tables generated from analysis result data
- Each figure/table gets a numbered caption and is referenced in text
- Consistent styling across all visual elements

## Quality Standards

### Content Quality
- Every claim backed by data or citation
- No unsupported generalizations
- Statistical claims include effect sizes and confidence intervals
- Methodology described in sufficient detail for replication

### Writing Quality
- Academic tone: formal, objective, precise
- No first person unless standard in the field
- Active voice preferred where appropriate
- Jargon defined on first use
- Consistent terminology throughout

### Formatting Quality
- Consistent heading hierarchy
- Numbered figures and tables with captions
- Properly formatted equations (if any)
- Page numbers and headers
- Clean, readable layout

## Automated Quality Checks

Before submission for human review, the system runs:

| Check | Description | Threshold |
|-------|-------------|-----------|
| Citation completeness | All claims have citations | 100% |
| Reference integrity | All citations resolve to references | 100% |
| Section completeness | All required sections present | 100% |
| Minimum length | Abstract ≥ 150 words, body ≥ 3000 words | Hard minimum |
| Readability | Flesch-Kincaid grade level | 12-16 (academic) |
| Figure references | All figures referenced in text | 100% |
| Consistency | Key terms used consistently | > 95% |

## Output Formats

- **Markdown** — Primary draft format, human-readable, version-controllable
- **LaTeX** — For publication-ready PDF generation
- **PDF** — Final compiled output
- **HTML** — For web viewing

## Revision Workflow

```
[Draft v1] → Quality Checks → [Submit for Review]
                                      ↓
                              [Human Feedback]
                                      ↓
                             [Targeted Revisions]
                                      ↓
                              [Draft v2] → Quality Checks → [Re-submit]
                                                                ↓
                                                          [Approved] → Archive
```

Each revision:
- Addresses specific feedback points
- Preserves a diff between versions
- Logs what changed and why
- Re-runs quality checks

## File Structure

```
report/
├── drafts/
│   ├── v1/
│   │   ├── whitepaper.md          # Full draft
│   │   ├── quality_report.yaml    # Quality check results
│   │   └── review_feedback.md     # Human feedback (if any)
│   └── v2/
│       ├── whitepaper.md
│       ├── quality_report.yaml
│       └── revision_notes.md      # What changed from v1
├── final/
│   ├── whitepaper.md              # Approved final version
│   ├── whitepaper.pdf             # Compiled PDF
│   └── whitepaper.tex             # LaTeX source (if generated)
└── assets/
    ├── figures/                   # Copies of figures used in report
    └── tables/                    # Generated table data
```
