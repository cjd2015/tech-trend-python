"""LLM Factory - Create LLM provider based on config"""
from __future__ import annotations
from .provider import LLMProvider
from .anthropic import AnthropicProvider
from .openai import OpenAIProvider
from .gemini import GeminiProvider
from ..config import LLM_PROVIDER, LLM_API_KEY, LLM_MODEL, OLLAMA_BASE_URL


def create_llm_provider() -> LLMProvider | None:
    if not LLM_PROVIDER:
        return None

    if not LLM_API_KEY and LLM_PROVIDER not in ["ollama", "codex"]:
        return None

    providers = {
        "anthropic": AnthropicProvider,
        "openai": OpenAIProvider,
        "gemini": GeminiProvider,
    }

    provider_class = providers.get(LLM_PROVIDER.lower())
    if provider_class:
        return provider_class(LLM_API_KEY, LLM_MODEL)

    return None
