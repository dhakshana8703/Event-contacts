"""Serper.dev live Google Search provider."""
import json
import os
import urllib.request
import urllib.error
from typing import List, Optional

from src.providers.base import BaseSearchProvider, SearchResult


class SerperSearchProvider(BaseSearchProvider):
    """Live Google Search provider using Serper.dev API."""

    ENDPOINT = "https://google.serper.dev/search"

    def __init__(self, api_key: Optional[str] = None, timeout: int = 10):
        self.api_key = api_key or os.getenv("SERPER_API_KEY")
        self.timeout = timeout

    def search(self, query: str, num_results: int = 5) -> List[SearchResult]:
        if not self.api_key:
            raise ValueError("SERPER_API_KEY environment variable is not set or provided.")

        payload = json.dumps({"q": query, "num": num_results}).encode("utf-8")
        req = urllib.request.Request(
            self.ENDPOINT,
            data=payload,
            headers={
                "X-API-KEY": self.api_key,
                "Content-Type": "application/json",
                "User-Agent": "NunifyEventIntelligencePOC/1.0"
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
            # Let caller handle or log network/API failure
            raise RuntimeError(f"Serper API search failed: {e}") from e

        results: List[SearchResult] = []
        organic = data.get("organic", [])
        for pos, item in enumerate(organic[:num_results], start=1):
            results.append(
                SearchResult(
                    title=item.get("title", ""),
                    url=item.get("link", ""),
                    snippet=item.get("snippet", ""),
                    source="serper",
                    position=pos
                )
            )

        return results
