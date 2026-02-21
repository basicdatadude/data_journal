"""Academic whitepaper template definitions."""

from __future__ import annotations

from shared.models.report import WHITEPAPER_SECTIONS, ReportSection

# Section titles and writing guidance for the AI drafter
SECTION_TEMPLATES = {
    "title_page": {
        "title": "Title Page",
        "guidance": "Generate a clear, descriptive title for the research paper. "
                    "Include the date and author attribution.",
    },
    "abstract": {
        "title": "Abstract",
        "guidance": "Write a 150-300 word summary covering the research question, "
                    "methodology, key findings, and implications. This should stand "
                    "alone as a complete summary of the paper.",
        "min_words": 150,
        "max_words": 300,
    },
    "introduction": {
        "title": "Introduction",
        "guidance": "Establish context for the research, state the problem or question "
                    "being investigated, explain the scope and significance, and outline "
                    "the structure of the paper.",
        "min_words": 300,
    },
    "literature_review": {
        "title": "Literature Review",
        "guidance": "Summarize relevant existing research and prior work. Show how this "
                    "research fits into the broader body of knowledge. Identify gaps "
                    "that this work addresses. Cite all referenced works.",
        "min_words": 400,
    },
    "methodology": {
        "title": "Methodology",
        "guidance": "Describe the data collection methods, data sources, analysis "
                    "techniques, and tools used. Provide sufficient detail for "
                    "replication. Justify methodological choices.",
        "min_words": 300,
    },
    "results": {
        "title": "Results",
        "guidance": "Present findings objectively with supporting data, tables, and "
                    "figures. Include statistical results with appropriate metrics. "
                    "Do not interpret — save that for the Discussion.",
        "min_words": 400,
    },
    "discussion": {
        "title": "Discussion",
        "guidance": "Interpret the results in context. Discuss implications, compare "
                    "with prior work, address limitations, and suggest explanations "
                    "for unexpected findings.",
        "min_words": 400,
    },
    "conclusion": {
        "title": "Conclusion",
        "guidance": "Summarize the key findings, state the contribution of this work, "
                    "discuss practical implications, and suggest directions for future "
                    "research.",
        "min_words": 200,
    },
    "references": {
        "title": "References",
        "guidance": "List all cited works in the chosen citation format (APA or IEEE). "
                    "Every inline citation must appear here, and every reference here "
                    "must be cited in the text.",
    },
    "appendices": {
        "title": "Appendices",
        "guidance": "Include supplementary material: additional data tables, extended "
                    "methodology details, code references, and supporting evidence "
                    "that would break the flow of the main text.",
    },
}


def create_empty_report_sections() -> list[ReportSection]:
    """Create the standard set of empty sections for a new whitepaper."""
    sections = []
    for section_name in WHITEPAPER_SECTIONS:
        template = SECTION_TEMPLATES.get(section_name, {})
        sections.append(ReportSection(
            name=section_name,
            title=template.get("title", section_name.replace("_", " ").title()),
        ))
    return sections


MARKDOWN_TEMPLATE = """# {title}

**Date:** {date}
**Project:** {project_name}

---

## Abstract

{abstract}

---

## 1. Introduction

{introduction}

## 2. Literature Review

{literature_review}

## 3. Methodology

{methodology}

## 4. Results

{results}

## 5. Discussion

{discussion}

## 6. Conclusion

{conclusion}

---

## References

{references}

---

## Appendices

{appendices}
"""

LATEX_TEMPLATE = r"""\documentclass[12pt,a4paper]{{article}}
\usepackage[utf8]{{inputenc}}
\usepackage{{amsmath,amssymb}}
\usepackage{{graphicx}}
\usepackage{{hyperref}}
\usepackage{{natbib}}
\usepackage{{geometry}}
\geometry{{margin=1in}}

\title{{{title}}}
\author{{Data Journal Research System}}
\date{{{date}}}

\begin{{document}}
\maketitle

\begin{{abstract}}
{abstract}
\end{{abstract}}

\section{{Introduction}}
{introduction}

\section{{Literature Review}}
{literature_review}

\section{{Methodology}}
{methodology}

\section{{Results}}
{results}

\section{{Discussion}}
{discussion}

\section{{Conclusion}}
{conclusion}

\bibliographystyle{{apalike}}
\bibliography{{references}}

\appendix
{appendices}

\end{{document}}
"""
