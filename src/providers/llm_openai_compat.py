"""OpenAI-compatible LLM provider for NVIDIA NIM, Groq, or OpenAI."""
import json
import os
import urllib.request
import urllib.error
from typing import Dict, Any, Optional

from src.providers.base import BaseLLMProvider


class OpenAICompatibleLLMProvider(BaseLLMProvider):
    """LLM provider compatible with any OpenAI-compatible API (NVIDIA NIM, Groq, OpenAI)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://integrate.api.nvidia.com/v1",
        model: str = "meta/llama-3.3-70b-instruct",
        api_key_env_var: str = "NVIDIA_API_KEY",
        timeout: int = 30
    ):
        self.api_key = api_key or os.getenv(api_key_env_var)
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key_env_var = api_key_env_var
        self.timeout = timeout

    def generate_json(self, prompt: str, schema: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not self.api_key:
            raise ValueError(f"{self.api_key_env_var} environment variable is not set or provided.")

        endpoint = f"{self.base_url}/chat/completions"

        payload_dict: Dict[str, Any] = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a precise data extraction specialist. Output valid JSON only, without markdown fences or extraneous text."
                },
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.0
        }

        # Some providers support response_format
        if "nvidia" not in self.base_url.lower():
            payload_dict["response_format"] = {"type": "json_object"}

        payload = json.dumps(payload_dict).encode("utf-8")

        req = urllib.request.Request(
            endpoint,
            data=payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "NunifyEventIntelligencePOC/1.0"
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
            raise RuntimeError(f"LLM API generation failed at {endpoint}: {e}") from e

        try:
            content = data["choices"][0]["message"]["content"].strip()
            # Clean possible markdown wrapping ```json ... ```
            if content.startswith("```"):
                lines = content.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                content = "\n".join(lines).strip()
            return json.loads(content)
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            raise ValueError(f"Failed to parse structured JSON from LLM response: {e}") from e
