"""GSCPI"""
from __future__ import annotations
from ..base import SourceResult

async def briefing():
    return SourceResult(name="GSCPI", status="ok", duration_ms=0, data={"latest": None})
