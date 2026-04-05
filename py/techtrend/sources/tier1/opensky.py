"""OpenSky Network - Flight tracking"""
from __future__ import annotations
import time
import httpx
from ..base import SourceResult


async def briefing():
    start = time.time()
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get("https://opensky-network.org/api/states/all")
            if response.status_code == 200:
                data = response.json()
                states = data.get("states") or []
                by_country = {}
                for s in states:
                    country = s[2] or "Unknown"
                    by_country[country] = by_country.get(country, 0) + 1
                top = dict(sorted(by_country.items(), key=lambda x: x[1], reverse=True)[:10])
                return SourceResult(
                    name="OpenSky", status="ok", duration_ms=(time.time()-start)*1000,
                    data={"total_aircraft": len(states), "by_country": top},
                )
    except Exception as e:
        return SourceResult(name="OpenSky", status="error", duration_ms=(time.time()-start)*1000, error=str(e))
    return SourceResult(name="OpenSky", status="error", duration_ms=(time.time()-start)*1000, error="fetch failed")
