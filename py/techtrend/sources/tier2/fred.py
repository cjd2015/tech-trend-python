"""FRED - Federal Reserve Economic Data"""
from __future__ import annotations
import time
from ..base import SourceResult, safe_fetch
from ...config import FRED_API_KEY


async def briefing():
    start = time.time()
    if not FRED_API_KEY:
        return SourceResult(name="FRED", status="error", duration_ms=(time.time()-start)*1000, error="No API key")
    
    indicators = []
    for sid in ["VIXCLS", "BAMLH0A0HYM2", "T10Y2Y", "DGS10", "DFF"]:
        url = "https://api.stlouisfed.org/fred/series/observations"
        params = {"series_id": sid, "api_key": FRED_API_KEY, "file_type": "json", "sort_order": "desc", "limit": 5}
        data = await safe_fetch(url, params=params)
        if data and "observations" in data:
            obs = [o for o in data["observations"] if o.get("value") != "."]
            if obs:
                indicators.append({"id": sid, "value": float(obs[0]["value"]), "date": obs[0]["date"]})
    
    return SourceResult(name="FRED", status="ok", duration_ms=(time.time()-start)*1000, data={"indicators": indicators})
