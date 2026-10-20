"""Mock LLM provider for deterministic offline testing."""
from typing import Dict, Any, Optional
from src.providers.base import BaseLLMProvider


class MockLLMProvider(BaseLLMProvider):
    """Offline mock LLM provider returning canned JSON structures."""

    def __init__(self, canned_response: Optional[Dict[str, Any]] = None):
        self.canned_response = canned_response or {}
        self.recorded_prompts: list[str] = []

    def set_canned_response(self, response: Dict[str, Any]):
        self.canned_response = response

    def generate_json(self, prompt: str, schema: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self.recorded_prompts.append(prompt)
        return self.canned_response
