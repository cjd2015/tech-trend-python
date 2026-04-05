"""Reddit"""
from __future__ import annotations
from ..base import SourceResult

async def briefing():
    return SourceResult(name="Reddit", status="ok", duration_ms=0, data={"posts": []})
