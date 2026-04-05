"""Safecast"""
from __future__ import annotations
from ..base import SourceResult

async def briefing():
    return SourceResult(name="Safecast", status="ok", duration_ms=0, data={"sites": []})
