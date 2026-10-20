"""Google Gemini LLM provider via REST API."""
import json
import os
import urllib.request
import urllib.error
from typing import Dict, Any, Optional

from src.providers.base import BaseLLMProvider


class GeminiLLMProvider(BaseLLMProvider):
    """LLM provider using Google AI Studio Gemini API."""

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-flash-lite-latest", timeout: int = 30):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model = model
        self.timeout = timeout

    def generate_json(self, prompt: str, schema: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set or provided.")

        endpoint = f"{self.BASE_URL}/{self.model}:generateContent?key={self.api_key}"

        gen_config: Dict[str, Any] = {
            "response_mime_type": "application/json",
            "temperature": 0.0  # Zero temperature for deterministic extraction
        }
        if schema:
            gen_config["response_schema"] = schema

        payload = json.dumps({
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": gen_config
        }).encode("utf-8")

        req = urllib.request.Request(
            endpoint,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "NunifyEventIntelligencePOC/1.0"
            },
            method="POST"
        )

        import time
        max_retries = 3
        data = None
        for attempt in range(max_retries):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    break
            except urllib.error.HTTPError as e:
                if e.code == 429 and attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 4
                    time.sleep(wait_time)
                    continue
                raise RuntimeError(f"Gemini API generation failed: {e}") from e
            except (urllib.error.URLError, TimeoutError) as e:
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                raise RuntimeError(f"Gemini API generation failed: {e}") from e

        try:
            candidates = data.get("candidates", [])
            if not candidates:
                raise ValueError("Gemini returned no candidates.")
            raw_text = candidates[0]["content"]["parts"][0]["text"]
            return json.loads(raw_text)
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            raise ValueError(f"Failed to parse structured JSON from Gemini response: {e}") from e
