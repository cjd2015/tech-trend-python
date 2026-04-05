"""CelesTrak - Satellite tracking"""
from __future__ import annotations
import time
import asyncio
from ..base import SourceResult, safe_fetch


async def fetch_group(group):
    url = "https://www.celestrak.org/NORAD/elements/gp.php"
    data = await safe_fetch(url, params={"GROUP": group, "FORMAT": "json"})
    return data if isinstance(data, list) else []


async def briefing():
    start = time.time()
    stations, starlink, recent = await asyncio.gather(
        fetch_group("stations"), fetch_group("starlink"), fetch_group("last-30-days")
    )
    iss = next((s for s in stations if "ISS" in s.get("OBJECT_NAME", "").upper()), None) if stations else None
    return SourceResult(
        name="Space", status="ok", duration_ms=(time.time()-start)*1000,
        data={"iss": iss, "constellations": {"starlink": len(starlink)}, "total_new_objects": len(recent)},
    )
