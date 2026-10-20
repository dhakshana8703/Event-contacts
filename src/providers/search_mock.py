"""Mock search provider for deterministic offline testing."""
from typing import List, Dict, Optional
from src.providers.base import BaseSearchProvider, SearchResult


class MockSearchProvider(BaseSearchProvider):
    """Offline mock search provider returning pre-configured search results."""

    def __init__(self, canned_results: Optional[Dict[str, List[SearchResult]]] = None):
        """
        Initialize with optional canned responses.
        Key: substring to match in the query (case-insensitive)
        Value: list of SearchResult objects
        """
        self.canned_results = canned_results or {}
        self.recorded_queries: List[str] = []

    def add_canned_result(self, query_substring: str, results: List[SearchResult]):
        """Register canned results for a specific query substring."""
        self.canned_results[query_substring.lower()] = results

    def search(self, query: str, num_results: int = 5) -> List[SearchResult]:
        """Return canned results if query matches any registered substring."""
        self.recorded_queries.append(query)
        q_lower = query.lower()

        for substring, results in self.canned_results.items():
            if substring in q_lower:
                return results[:num_results]

        return []
