"""Base crawler interface and shared crawling utilities."""

from __future__ import annotations

import hashlib
import time
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any

from shared.models.data import DataRecord, FetchResult, Provenance, SearchResult
from shared.utils.logging import get_logger

logger = get_logger("crawler")


class RateLimiter:
    """Token-bucket rate limiter for polite crawling."""

    def __init__(self, requests_per_second: float = 1.0, burst_limit: int = 5):
        self.rps = requests_per_second
        self.burst_limit = burst_limit
        self._tokens = float(burst_limit)
        self._last_refill = time.monotonic()

    def acquire(self):
        """Block until a request token is available."""
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self.burst_limit, self._tokens + elapsed * self.rps)
        self._last_refill = now

        if self._tokens < 1.0:
            wait = (1.0 - self._tokens) / self.rps
            time.sleep(wait)
            self._tokens = 0.0
            self._last_refill = time.monotonic()
        else:
            self._tokens -= 1.0


class BaseCrawler(ABC):
    """Abstract base class for all data crawlers.

    Subclasses must implement search(), fetch(), validate(), and extract().
    """

    crawler_name: str = "base"

    def __init__(
        self,
        rate_limiter: RateLimiter | None = None,
        timeout_seconds: int = 30,
        max_retries: int = 3,
        user_agent: str = "DataJournal-Research-Bot/1.0",
        cache_dir: Path | None = None,
    ):
        self.rate_limiter = rate_limiter or RateLimiter()
        self.timeout = timeout_seconds
        self.max_retries = max_retries
        self.user_agent = user_agent
        self.cache_dir = cache_dir

    @abstractmethod
    def search(self, query: str, **kwargs) -> list[SearchResult]:
        """Search for results matching the query."""

    @abstractmethod
    def fetch(self, url: str, **kwargs) -> FetchResult:
        """Fetch content from a URL."""

    def validate(self, result: FetchResult) -> bool:
        """Validate a fetch result. Override for crawler-specific validation."""
        if not result.content or not result.content.strip():
            return False
        if result.status_code >= 400:
            return False
        return True

    @abstractmethod
    def extract(self, result: FetchResult) -> DataRecord:
        """Extract a structured DataRecord from a FetchResult."""

    def _make_provenance(
        self, url: str, content: str, query_context: str = ""
    ) -> Provenance:
        """Create a provenance record for crawled content."""
        return Provenance(
            source_url=url,
            source_type=self._source_type(),
            access_date=datetime.utcnow().isoformat() + "Z",
            content_hash=f"sha256:{hashlib.sha256(content.encode()).hexdigest()}",
            crawler=self.crawler_name,
            query_context=query_context,
        )

    def _source_type(self) -> str:
        """Override to set the source type for provenance records."""
        return "web_page"

    def _retry_fetch(self, url: str, **kwargs) -> FetchResult:
        """Fetch with retry and exponential backoff."""
        backoff_times = [2, 4, 8]
        last_error: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                self.rate_limiter.acquire()
                return self.fetch(url, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < self.max_retries:
                    wait = backoff_times[min(attempt, len(backoff_times) - 1)]
                    logger.warning(
                        "Fetch failed for %s (attempt %d/%d), retrying in %ds: %s",
                        url, attempt + 1, self.max_retries + 1, wait, e,
                    )
                    time.sleep(wait)

        raise last_error  # type: ignore[misc]

    def crawl(self, query: str, max_results: int = 10, **kwargs) -> list[DataRecord]:
        """Full crawl pipeline: search → fetch → validate → extract.

        Returns a list of DataRecords from validated results.
        """
        logger.info("Crawling for query: %s (max_results=%d)", query, max_results)
        results = self.search(query, max_results=max_results, **kwargs)
        records: list[DataRecord] = []

        for search_result in results[:max_results]:
            try:
                fetch_result = self._retry_fetch(search_result.url)
                if not self.validate(fetch_result):
                    logger.warning("Validation failed for %s, skipping", search_result.url)
                    continue
                record = self.extract(fetch_result)
                record.provenance.query_context = query
                records.append(record)
            except Exception as e:
                logger.error("Failed to process %s: %s", search_result.url, e)
                continue

        logger.info("Crawl complete: %d records from %d search results", len(records), len(results))
        return records
