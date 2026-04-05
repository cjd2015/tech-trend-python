"""Base classes and utilities for all data sources"""
from __future__ import annotations
import asyncio
import time
from dataclasses import dataclass
from typing import Any, Optional, Dict, List
import httpx


@dataclass
class SourceResult:
    name: str
    status: str
    duration_ms: float
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.status == "ok"


async def safe_fetch(
    url: str,
    timeout: float = 30.0,
    headers: Optional[Dict] = None,
    params: Optional[Dict] = None,
    method: str = "GET",
    json: Optional[Dict] = None,
) -> Optional[Dict]:
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            if method == "POST":
                response = await client.post(url, headers=headers, json=json)
            else:
                response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        return {"error": str(e)}


async def http_get(
    url: str,
    timeout: float = 30.0,
    headers: Optional[Dict] = None,
    params: Optional[Dict] = None,
) -> Optional[str]:
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.text
    except Exception:
        return None
