"""LLM Base Provider"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional
import httpx


class LLMProvider(ABC):
    def __init__(self, api_key: str, model: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self._configured = bool(api_key)

    @property
    def is_configured(self) -> bool:
        return self._configured

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    async def complete(self, prompt: str, system: Optional[str] = None) -> str:
        pass

    async def close(self):
        pass
