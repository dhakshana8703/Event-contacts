"""Base interfaces and data structures for interchangeable Search and LLM Providers."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any


@dataclass
class SearchResult:
    """Standardized search result item across all search engines."""
    title: str
    url: str
    snippet: str
    source: str  # e.g., 'serper', 'tavily', 'mock'
    position: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class BaseSearchProvider(ABC):
    """Abstract interface for web and LinkedIn search providers."""

    @abstractmethod
    def search(self, query: str, num_results: int = 5) -> List[SearchResult]:
        """
        Execute a search query and return standardized SearchResults.

        Args:
            query: The search query string (e.g. site:linkedin.com/in "Name" "Org")
            num_results: Maximum number of results to retrieve.

        Returns:
            List of SearchResult objects.
        """
        pass


class BaseLLMProvider(ABC):
    """Abstract interface for LLM reasoning and extraction providers."""

    @abstractmethod
    def generate_json(self, prompt: str, schema: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate structured JSON output from an LLM prompt.

        Args:
            prompt: Text prompt with instructions and source evidence.
            schema: Optional JSON schema definition to enforce.

        Returns:
            Parsed JSON response as a dictionary.
        """
        pass
