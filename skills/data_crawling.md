# Skill: Data Crawling

## Purpose

Systematically discover and retrieve data from the web and other sources for research projects. The crawling layer provides pluggable crawlers that agents invoke to collect raw data.

## Architecture

### Crawler Interface

All crawlers implement a common interface:

```python
class BaseCrawler:
    def search(self, query: str, **kwargs) -> list[SearchResult]
    def fetch(self, url: str, **kwargs) -> FetchResult
    def validate(self, result: FetchResult) -> bool
    def extract(self, result: FetchResult) -> DataRecord
```

### Available Crawlers

#### Web Search Crawler
- Searches the web using search APIs (Google, Bing, DuckDuckGo)
- Returns ranked results with snippets and URLs
- Supports filtering by date range, domain, content type
- Rate-limited to respect API quotas

#### Web Page Extractor
- Fetches and parses HTML pages
- Extracts main content (strips nav, ads, boilerplate)
- Preserves tables, lists, and structured data
- Handles JavaScript-rendered pages when needed (via headless browser)

#### Academic Paper Fetcher
- Searches arXiv, Semantic Scholar, PubMed, Google Scholar
- Retrieves paper metadata (title, authors, abstract, citations)
- Downloads PDFs when available and permitted
- Extracts structured content from papers

#### Dataset Fetcher
- Queries public data portals (data.gov, World Bank, UN Data, etc.)
- Downloads datasets in CSV, JSON, Excel formats
- Retrieves API data from public REST endpoints
- Handles pagination and large dataset streaming

#### News & Media Crawler
- Searches news archives and RSS feeds
- Extracts article text, publication date, author, outlet
- Supports date-range filtering for historical research
- Handles paywalled content gracefully (metadata only)

## Data Provenance

Every piece of collected data includes provenance metadata:

```yaml
provenance:
  source_url: "https://example.com/data"
  source_type: web_page | academic_paper | dataset | news_article
  access_date: "2026-02-21T14:30:00Z"
  content_hash: "sha256:abc123..."
  crawler: web_page_extractor
  query_context: "original search query that led here"
  reliability_score: 0.85  # estimated source quality
```

## Politeness & Ethics

- Respect `robots.txt` directives
- Rate limit all requests (configurable per-domain)
- Identify the crawler via User-Agent string
- Cache responses to avoid redundant requests
- Never circumvent access controls or paywalls
- Log all access for audit purposes

## Configuration

```yaml
crawling:
  rate_limit:
    requests_per_second: 1
    burst_limit: 5
  cache:
    enabled: true
    ttl_hours: 24
    max_size_mb: 500
  user_agent: "DataJournal-Research-Bot/1.0"
  timeout_seconds: 30
  max_retries: 3
  retry_backoff_seconds: [2, 4, 8]
```

## Output

Crawled data is stored in the project's `data/raw/` directory with accompanying metadata files:

```
data/raw/
├── source_001.json       # extracted content
├── source_001.meta.yaml  # provenance metadata
├── source_002.json
├── source_002.meta.yaml
└── crawl_manifest.yaml   # index of all crawled sources
```
