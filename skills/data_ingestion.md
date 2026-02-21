# Skill: Data Ingestion

## Purpose

Transform raw crawled data into clean, normalized, queryable datasets ready for analysis. The ingestion pipeline bridges the gap between messy real-world data and the structured inputs the analysis engine requires.

## Pipeline Stages

```
RAW DATA → EXTRACT → CLEAN → NORMALIZE → DEDUPLICATE → VALIDATE → STORE
```

### 1. Extract
- Parse raw files (HTML, PDF, JSON, CSV, XML)
- Extract text content from documents
- Extract structured data from tables and APIs
- Handle encoding issues (UTF-8 normalization)

### 2. Clean
- Remove HTML tags, special characters, and formatting artifacts
- Fix broken encoding and unicode issues
- Strip boilerplate content (headers, footers, navigation)
- Handle missing values (mark as null, impute where appropriate)

### 3. Normalize
- Standardize date formats to ISO 8601
- Normalize numeric formats (currency, units, percentages)
- Standardize categorical values (case, spelling, synonyms)
- Apply consistent schema to heterogeneous sources

### 4. Deduplicate
- Content-based deduplication using similarity hashing
- Detect near-duplicates using fuzzy matching
- Merge records from multiple sources about the same entity
- Preserve the highest-quality version when duplicates conflict

### 5. Validate
- Schema validation against expected data models
- Range checks for numeric values
- Referential integrity checks
- Quality scoring per record (completeness, consistency, timeliness)

### 6. Store
- Write processed records to `data/processed/` in the project directory
- Update the data index/catalog
- Generate ingestion report (records processed, errors, quality summary)

## Data Quality Scoring

Each record receives a quality score (0.0 to 1.0) based on:

| Factor | Weight | Description |
|--------|--------|-------------|
| Completeness | 0.25 | Are all expected fields populated? |
| Accuracy | 0.25 | Do values pass validation checks? |
| Timeliness | 0.20 | How recent is the data? |
| Consistency | 0.15 | Does it agree with other sources? |
| Provenance | 0.15 | Is the source reliable and well-documented? |

## Output Format

Processed data is stored as structured JSON or CSV with a consistent schema:

```
data/processed/
├── dataset.csv              # tabular data (if applicable)
├── dataset.json             # structured records
├── text_corpus.jsonl        # text documents (one per line)
├── quality_report.yaml      # quality metrics summary
└── ingestion_log.jsonl      # processing log with errors/warnings
```

## Error Handling

- Malformed records: log warning, skip or quarantine to `data/errors/`
- Schema violations: attempt coercion, quarantine if impossible
- Encoding errors: attempt detection and conversion, flag if unresolvable
- All errors are non-fatal at the record level — the pipeline continues processing
