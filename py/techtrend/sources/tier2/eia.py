"""EIA - US Energy Information Administration"""
from __future__ import annotations
import time
from ..base import SourceResult, safe_fetch
from ...config import EIA_API_KEY


async def briefing():
    start = time.time()
    if not EIA_API_KEY:
        return SourceResult(name="EIA", status="error", duration_ms=(time.time()-start)*1000, error="No API key")
    
    prices = {}
    for sid, key in [("PET.RWTC.D", "wti"), ("PET.Brent.D", "brent")]:
        url = "https://api.eia.gov/v2/petroleum/pri/sum/data/"
        params = {"api_key": EIA_API_KEY, "frequency": "daily", "data[0]": "value", "facets[series][]": sid, "length": 5}
        data = await safe_fetch(url, params=params)
        if data and "response" in data:
            vals = data["response"].get("data", [])
            if vals:
                prices[key] = {"value": float(vals[0]["value"]), "date": vals[0]["period"]}
    
    return SourceResult(name="EIA", status="ok", duration_ms=(time.time()-start)*1000, data={"oil_prices": prices})
