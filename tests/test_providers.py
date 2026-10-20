"""Tests for interchangeable Search and LLM Provider Layer."""
import pytest
from src.providers.base import SearchResult
from src.providers.search_mock import MockSearchProvider
from src.providers.search_serper import SerperSearchProvider
from src.providers.search_tavily import TavilySearchProvider
from src.providers.llm_mock import MockLLMProvider
from src.providers.llm_gemini import GeminiLLMProvider
from src.providers.llm_openai_compat import OpenAICompatibleLLMProvider


class TestSearchProviders:
    def test_mock_search_provider_returns_canned_results(self):
        mock = MockSearchProvider()
        mock.add_canned_result("wetex", [
            SearchResult(title="WETEX Official", url="https://wetex.ae", snippet="Water & Energy", source="mock"),
            SearchResult(title="WETEX Committee", url="https://wetex.ae/team", snippet="Committee", source="mock"),
        ])

        results = mock.search('site:linkedin.com "WETEX"', num_results=1)
        assert len(results) == 1
        assert results[0].url == "https://wetex.ae"
        assert results[0].source == "mock"
        assert len(mock.recorded_queries) == 1

    def test_mock_search_provider_no_match(self):
        mock = MockSearchProvider()
        results = mock.search("unknown query")
        assert results == []

    def test_serper_missing_key_raises_value_error(self, monkeypatch):
        monkeypatch.delenv("SERPER_API_KEY", raising=False)
        provider = SerperSearchProvider(api_key=None)
        with pytest.raises(ValueError, match="SERPER_API_KEY"):
            provider.search("test query")

    def test_tavily_missing_key_raises_value_error(self, monkeypatch):
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)
        provider = TavilySearchProvider(api_key=None)
        with pytest.raises(ValueError, match="TAVILY_API_KEY"):
            provider.search("test query")


class TestLLMProviders:
    def test_mock_llm_provider_returns_json(self):
        canned = {"contacts": [{"name": "Olga Melnikova", "role": "Organizer"}]}
        mock = MockLLMProvider(canned_response=canned)

        result = mock.generate_json("Extract contacts")
        assert result == canned
        assert len(mock.recorded_prompts) == 1

    def test_gemini_missing_key_raises_value_error(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        provider = GeminiLLMProvider(api_key=None)
        with pytest.raises(ValueError, match="GEMINI_API_KEY"):
            provider.generate_json("prompt")

    def test_openai_compat_missing_key_raises_value_error(self, monkeypatch):
        monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
        provider = OpenAICompatibleLLMProvider(api_key=None, api_key_env_var="NVIDIA_API_KEY")
        with pytest.raises(ValueError, match="NVIDIA_API_KEY"):
            provider.generate_json("prompt")
