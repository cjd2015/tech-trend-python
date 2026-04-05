from dataclasses import dataclass, field
from typing import Any
from datetime import datetime


@dataclass
class SourceResult:
    name: str
    status: str
    duration_ms: float
    data: dict[str, Any] | None = None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.status == "ok"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "data": self.data,
            "error": self.error,
        }


async def safe_fetch(
    url: str,
    timeout: float = 30.0,
    headers: dict | None = None,
    params: dict | None = None,
) -> dict | None:
    """Fetch JSON with timeout and error handling."""
    import httpx
    
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        return {"error": str(e)}
