"""Telegram"""
from __future__ import annotations
from ..base import SourceResult

async def briefing():
    return SourceResult(name="Telegram", status="ok", duration_ms=0, data={"total_posts": 0, "urgent_posts": []})
