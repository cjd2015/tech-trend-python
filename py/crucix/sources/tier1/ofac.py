"""OFAC"""
from __future__ import annotations
from ..base import SourceResult

async def briefing():
    return SourceResult(name="OFAC", status="ok", duration_ms=0, data={"sdn_count": 0})
