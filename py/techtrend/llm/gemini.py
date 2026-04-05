"""Google Gemini Provider"""
from __future__ import annotations
from typing import Optional, List, Dict
from .provider import LLMProvider
import httpx


class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str, model: Optional[str] = None):
        super().__init__(api_key, model or "gemini-2.5-pro")
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    @property
    def name(self) -> str:
        return "Google Gemini"

    async def complete(self, prompt: str, system: Optional[str] = None) -> str:
        if not self.api_key:
            raise ValueError("No API key configured")

        url = f"{self.base_url}/models/{self.model}:generateContent"
        params = {"key": self.api_key}

        contents: List[Dict] = [{"parts": [{"text": prompt}]}]
        if system:
            contents.insert(0, {"parts": [{"text": system}]})

        body = {"contents": contents}

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, params=params, json=body)
            response.raise_for_status()
            data = response.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
