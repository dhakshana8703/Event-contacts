"""Tavily AI live search provider."""
import json
import os
import urllib.request
import urllib.error
from typing import List, Optional

from src.providers.base import BaseSearchProvider, SearchResult


class TavilySearchProvider(BaseSearchProvider):
    """Live web search provider using Tavily API."""

    ENDPOINT = "https://api.tavily.com/search"

    def __init__(self, api_key: Optional[str] = None, timeout: int = 10):
        self.api_key = api_key or os.getenv("TAVILY_API_KEY")
        self.timeout = timeout

    def search(self, query: str, num_results: int = 5) -> List[SearchResult]:
        if not self.api_key:
            raise ValueError("TAVILY_API_KEY environment variable is not set or provided.")

        payload = json.dumps({
            "api_key": self.api_key,
            "query": query,
            "max_results": num_results,
            "search_depth": "basic"
        }).encode("utf-8")

        req = urllib.request.Request(
            self.ENDPOINT,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "NunifyEventIntelligencePOC/1.0"
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
            raise RuntimeError(f"Tavily API search failed: {e}") from e

        results: List[SearchResult] = []
        for pos, item in enumerate(data.get("results", [])[:num_results], start=1):
            results.append(
                SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("content", ""),
                    source="tavily",
                    position=pos
                )
            )

        return results
