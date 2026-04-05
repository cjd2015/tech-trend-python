"""NOAA"""
from __future__ import annotations
from ..base import SourceResult

async def briefing():
    return SourceResult(name="NOAA", status="ok", duration_ms=0, data={"total_alerts": 0})
