"""Providers module: interchangeable search and LLM adapters."""
from src.providers.base import BaseSearchProvider, BaseLLMProvider, SearchResult
from src.providers.search_mock import MockSearchProvider
from src.providers.search_serper import SerperSearchProvider
from src.providers.search_tavily import TavilySearchProvider
from src.providers.llm_mock import MockLLMProvider
from src.providers.llm_gemini import GeminiLLMProvider
from src.providers.llm_openai_compat import OpenAICompatibleLLMProvider

__all__ = [
    "BaseSearchProvider",
    "BaseLLMProvider",
    "SearchResult",
    "MockSearchProvider",
    "SerperSearchProvider",
    "TavilySearchProvider",
    "MockLLMProvider",
    "GeminiLLMProvider",
    "OpenAICompatibleLLMProvider",
]
