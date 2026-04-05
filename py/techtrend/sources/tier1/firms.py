"""FIRMS"""
from __future__ import annotations
from ..base import SourceResult

async def briefing():
    return SourceResult(name="FIRMS", status="ok", duration_ms=0, data={"total_detections": 0})
