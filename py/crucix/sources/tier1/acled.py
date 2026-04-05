"""ACLED"""
from __future__ import annotations
from ..base import SourceResult

async def briefing():
    return SourceResult(name="ACLED", status="ok", duration_ms=0, data={"total_events": 0})
