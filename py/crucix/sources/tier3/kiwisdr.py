"""KiwiSDR"""
from __future__ import annotations
from ..base import SourceResult

async def briefing():
    return SourceResult(name="KiwiSDR", status="ok", duration_ms=0, data={"network": {"total_receivers": 0}})
