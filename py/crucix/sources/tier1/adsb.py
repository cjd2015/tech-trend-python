"""ADS-B"""
from __future__ import annotations
from ..base import SourceResult

async def briefing():
    return SourceResult(name="ADS-B", status="ok", duration_ms=0, data={"total_aircraft": 0})
