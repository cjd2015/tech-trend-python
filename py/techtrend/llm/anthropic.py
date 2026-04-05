"""Anthropic Claude Provider"""
from __future__ import annotations
from typing import Optional
from .provider import LLMProvider
import httpx


class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str, model: Optional[str] = None):
        super().__init__(api_key, model or "claude-sonnet-4-6")
        self.base_url = "https://api.anthropic.com"

    @property
    def name(self) -> str:
        return "Anthropic Claude"

    async def complete(self, prompt: str, system: Optional[str] = None) -> str:
        if not self.api_key:
            raise ValueError("No API key configured")

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        body = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}],
        }

        if system:
            body["system"] = system

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/v1/messages",
                headers=headers,
                json=body,
            )
            response.raise_for_status()
            data = response.json()
            return data["content"][0]["text"]
