"""OpenAI GPT Provider"""
from __future__ import annotations
from typing import Optional, List, Dict
from .provider import LLMProvider
import httpx


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: Optional[str] = None):
        super().__init__(api_key, model or "gpt-4o")
        self.base_url = "https://api.openai.com/v1"

    @property
    def name(self) -> str:
        return "OpenAI GPT"

    async def complete(self, prompt: str, system: Optional[str] = None) -> str:
        if not self.api_key:
            raise ValueError("No API key configured")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "content-type": "application/json",
        }

        messages: List[Dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        body = {
            "model": self.model,
            "messages": messages,
            "max_tokens": 4096,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=body,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
