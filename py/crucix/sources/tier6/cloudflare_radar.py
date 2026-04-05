"""Cloudflare Radar"""
from __future__ import annotations
from ..base import SourceResult

async def briefing():
    return SourceResult(name="Cloudflare-Radar", status="ok", duration_ms=0, data={"active_outages": []})
