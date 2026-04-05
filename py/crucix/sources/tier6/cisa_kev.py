"""CISA KEV"""
from __future__ import annotations
from ..base import SourceResult

async def briefing():
    return SourceResult(name="CISA-KEV", status="ok", duration_ms=0, data={"total": 0})
