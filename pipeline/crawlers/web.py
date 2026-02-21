"""Web search and page extraction crawlers."""

from __future__ import annotations

import re
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from typing import Any

from shared.models.data import DataRecord, FetchResult, SearchResult
from pipeline.crawlers.base import BaseCrawler, RateLimiter
from shared.utils.logging import get_logger

logger = get_logger("crawler.web")


class HTMLTextExtractor(HTMLParser):
    """Extract readable text from HTML, stripping tags and scripts."""

    def __init__(self):
        super().__init__()
        self._text_parts: list[str] = []
        self._skip_tags = {"script", "style", "nav", "header", "footer", "aside"}
        self._skip_depth = 0
        self._title = ""
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]):
        if tag in self._skip_tags:
            self._skip_depth += 1
        if tag == "title":
            self._in_title = True

    def handle_endtag(self, tag: str):
        if tag in self._skip_tags and self._skip_depth > 0:
            self._skip_depth -= 1
        if tag == "title":
            self._in_title = False
        if tag in ("p", "br", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li"):
            self._text_parts.append("\n")

    def handle_data(self, data: str):
        if self._in_title:
            self._title += data
        if self._skip_depth == 0:
            self._text_parts.append(data)

    @property
    def text(self) -> str:
        raw = "".join(self._text_parts)
        # Collapse whitespace
        lines = [line.strip() for line in raw.split("\n")]
        return "\n".join(line for line in lines if line)

    @property
    def title(self) -> str:
        return self._title.strip()


class WebSearchCrawler(BaseCrawler):
    """Crawler that searches the web and extracts page content.

    Uses urllib for HTTP requests (no external dependencies).
    For production, integrate with a search API (Google, Bing, etc.).
    """

    crawler_name = "web_search"

    def __init__(self, search_api_key: str = "", **kwargs):
        super().__init__(**kwargs)
        self.search_api_key = search_api_key

    def search(self, query: str, max_results: int = 10, **kwargs) -> list[SearchResult]:
        """Search the web for results matching the query.

        This is a placeholder that constructs search URLs.
        In production, integrate with a search API for proper results.
        """
        # Placeholder: return a structured search-like result
        # In production, call Google Custom Search, Bing Search API, or SerpAPI
        logger.info("Web search for: %s", query)
        encoded_query = urllib.parse.quote_plus(query)

        # Return the query as a single result pointing to a search engine
        # Real implementation would parse API response into multiple results
        return [
            SearchResult(
                url=f"https://www.google.com/search?q={encoded_query}",
                title=f"Search results for: {query}",
                snippet="",
                rank=1,
            )
        ]

    def fetch(self, url: str, **kwargs) -> FetchResult:
        """Fetch a web page."""
        self.rate_limiter.acquire()
        req = urllib.request.Request(url, headers={"User-Agent": self.user_agent})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                content = response.read().decode("utf-8", errors="replace")
                headers = dict(response.headers.items())
                return FetchResult(
                    url=url,
                    content=content,
                    status_code=response.status,
                    headers=headers,
                    content_type=headers.get("Content-Type", "text/html"),
                )
        except Exception as e:
            logger.error("Failed to fetch %s: %s", url, e)
            return FetchResult(url=url, content="", status_code=0)

    def extract(self, result: FetchResult) -> DataRecord:
        """Extract text content from an HTML page."""
        extractor = HTMLTextExtractor()
        try:
            extractor.feed(result.content)
        except Exception:
            pass

        return DataRecord(
            content=extractor.text,
            title=extractor.title,
            source_url=result.url,
            provenance=self._make_provenance(result.url, result.content),
        )

    def _source_type(self) -> str:
        return "web_page"


class AcademicCrawler(BaseCrawler):
    """Crawler for academic papers from arXiv, Semantic Scholar, etc.

    Uses public APIs that don't require authentication.
    """

    crawler_name = "academic"

    def search(self, query: str, max_results: int = 10, **kwargs) -> list[SearchResult]:
        """Search arXiv for papers matching the query."""
        import urllib.request
        import xml.etree.ElementTree as ET

        encoded = urllib.parse.quote(query)
        api_url = (
            f"http://export.arxiv.org/api/query?"
            f"search_query=all:{encoded}&start=0&max_results={max_results}"
        )

        self.rate_limiter.acquire()
        req = urllib.request.Request(api_url, headers={"User-Agent": self.user_agent})
        results: list[SearchResult] = []

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                xml_content = response.read().decode("utf-8")
                root = ET.fromstring(xml_content)
                ns = {"atom": "http://www.w3.org/2005/Atom"}

                for i, entry in enumerate(root.findall("atom:entry", ns)):
                    title_el = entry.find("atom:title", ns)
                    summary_el = entry.find("atom:summary", ns)
                    link_el = entry.find("atom:id", ns)

                    title = title_el.text.strip() if title_el is not None and title_el.text else ""
                    snippet = summary_el.text.strip()[:300] if summary_el is not None and summary_el.text else ""
                    url = link_el.text.strip() if link_el is not None and link_el.text else ""

                    if url:
                        results.append(SearchResult(url=url, title=title, snippet=snippet, rank=i + 1))
        except Exception as e:
            logger.error("arXiv search failed: %s", e)

        return results

    def fetch(self, url: str, **kwargs) -> FetchResult:
        """Fetch an arXiv paper's abstract page."""
        # Convert arXiv ID URL to abstract page
        abs_url = url.replace("/abs/", "/abs/").replace("/pdf/", "/abs/")
        self.rate_limiter.acquire()
        req = urllib.request.Request(abs_url, headers={"User-Agent": self.user_agent})

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                content = response.read().decode("utf-8", errors="replace")
                return FetchResult(url=abs_url, content=content, status_code=response.status)
        except Exception as e:
            logger.error("Failed to fetch %s: %s", abs_url, e)
            return FetchResult(url=abs_url, content="", status_code=0)

    def extract(self, result: FetchResult) -> DataRecord:
        """Extract paper metadata from the fetched content."""
        extractor = HTMLTextExtractor()
        try:
            extractor.feed(result.content)
        except Exception:
            pass

        return DataRecord(
            content=extractor.text,
            title=extractor.title,
            source_url=result.url,
            provenance=self._make_provenance(result.url, result.content),
            metadata={"source_type": "academic_paper"},
        )

    def _source_type(self) -> str:
        return "academic_paper"


class DatasetCrawler(BaseCrawler):
    """Crawler for public datasets from data portals and APIs."""

    crawler_name = "dataset"

    def search(self, query: str, max_results: int = 10, **kwargs) -> list[SearchResult]:
        """Search data.gov for datasets. Placeholder for broader dataset discovery."""
        encoded = urllib.parse.quote(query)
        api_url = f"https://catalog.data.gov/api/3/action/package_search?q={encoded}&rows={max_results}"

        self.rate_limiter.acquire()
        req = urllib.request.Request(api_url, headers={"User-Agent": self.user_agent})
        results: list[SearchResult] = []

        try:
            import json
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
                for i, pkg in enumerate(data.get("result", {}).get("results", [])):
                    title = pkg.get("title", "")
                    notes = pkg.get("notes", "")[:200]
                    url = pkg.get("url") or f"https://catalog.data.gov/dataset/{pkg.get('name', '')}"
                    results.append(SearchResult(url=url, title=title, snippet=notes, rank=i + 1))
        except Exception as e:
            logger.error("Dataset search failed: %s", e)

        return results

    def fetch(self, url: str, **kwargs) -> FetchResult:
        """Fetch dataset metadata or content from a URL."""
        self.rate_limiter.acquire()
        req = urllib.request.Request(url, headers={"User-Agent": self.user_agent})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                content = response.read().decode("utf-8", errors="replace")
                return FetchResult(url=url, content=content, status_code=response.status)
        except Exception as e:
            logger.error("Failed to fetch dataset %s: %s", url, e)
            return FetchResult(url=url, content="", status_code=0)

    def extract(self, result: FetchResult) -> DataRecord:
        """Extract dataset information from fetched content."""
        # Try JSON first, then fall back to HTML extraction
        content = result.content.strip()
        try:
            import json
            data = json.loads(content)
            title = data.get("title", data.get("name", ""))
            description = data.get("description", data.get("notes", ""))
            return DataRecord(
                content=description or str(data),
                title=title,
                source_url=result.url,
                provenance=self._make_provenance(result.url, content),
                metadata={"format": "json", "source_type": "dataset"},
            )
        except (json.JSONDecodeError, ValueError):
            pass

        extractor = HTMLTextExtractor()
        try:
            extractor.feed(content)
        except Exception:
            pass

        return DataRecord(
            content=extractor.text or content[:5000],
            title=extractor.title,
            source_url=result.url,
            provenance=self._make_provenance(result.url, content),
            metadata={"source_type": "dataset"},
        )

    def _source_type(self) -> str:
        return "dataset"


class NewsCrawler(BaseCrawler):
    """Crawler for news articles and media content."""

    crawler_name = "news"

    def search(self, query: str, max_results: int = 10, **kwargs) -> list[SearchResult]:
        """Search for news articles. Placeholder for news API integration."""
        logger.info("News search for: %s", query)
        # In production, integrate with NewsAPI, Google News RSS, etc.
        return []

    def fetch(self, url: str, **kwargs) -> FetchResult:
        """Fetch a news article."""
        self.rate_limiter.acquire()
        req = urllib.request.Request(url, headers={"User-Agent": self.user_agent})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                content = response.read().decode("utf-8", errors="replace")
                return FetchResult(url=url, content=content, status_code=response.status)
        except Exception as e:
            logger.error("Failed to fetch news %s: %s", url, e)
            return FetchResult(url=url, content="", status_code=0)

    def extract(self, result: FetchResult) -> DataRecord:
        """Extract article text from a news page."""
        extractor = HTMLTextExtractor()
        try:
            extractor.feed(result.content)
        except Exception:
            pass

        return DataRecord(
            content=extractor.text,
            title=extractor.title,
            source_url=result.url,
            provenance=self._make_provenance(result.url, result.content),
            metadata={"source_type": "news_article"},
        )

    def _source_type(self) -> str:
        return "news_article"


def get_crawler(crawler_type: str, **kwargs) -> BaseCrawler:
    """Factory function to get a crawler by type."""
    crawlers = {
        "web_search": WebSearchCrawler,
        "academic": AcademicCrawler,
        "dataset": DatasetCrawler,
        "news": NewsCrawler,
    }
    cls = crawlers.get(crawler_type)
    if cls is None:
        raise ValueError(f"Unknown crawler type: {crawler_type}. Available: {list(crawlers.keys())}")
    return cls(**kwargs)
