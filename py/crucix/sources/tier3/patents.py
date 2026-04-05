"""Patents"""
from __future__ import annotations
from ..base import SourceResult

async def briefing():
    return SourceResult(name="Patents", status="ok", duration_ms=0, data={"domains": {}})
