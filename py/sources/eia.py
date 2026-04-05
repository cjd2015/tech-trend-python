"""EIA - US Energy Information Administration (free API key)"""
import time
from .base import safe_fetch, SourceResult
from config import EIA_API_KEY


async def fetch_eia() -> SourceResult:
    start = time.time()
    
    if not EIA_API_KEY:
        return SourceResult(
            name="EIA",
            status="error",
            duration_ms=(time.time() - start) * 1000,
            error="No EIA API key. Get free at https://api.eia.gov/opendata/register.php",
        )
    
    signals = []
    oil_prices = {}
    
    endpoints = [
        ("PET.RWTC.D", "WTI Crude"),
        ("PET.Brent.D", "Brent Crude"),
    ]
    
    for series_id, label in endpoints:
        url = "https://api.eia.gov/v2/petroleum/pri/sum/data/"
        params = {
            "api_key": EIA_API_KEY,
            "frequency": "daily",
            "data[0]": "value",
            "facets[series][]": series_id,
            "sort[0][column]": "period",
            "sort[0][direction]": "desc",
            "length": 5,
        }
        
        data = await safe_fetch(url, params=params)
        
        if data and "error" not in data:
            values = data.get("response", {}).get("data", [])
            if values:
                latest = values[0]
                price = latest.get("value")
                if price:
                    key = "wti" if "WTI" in label else "brent"
                    oil_prices[key] = {
                        "label": label,
                        "value": float(price),
                        "date": latest.get("period"),
                    }
    
    return SourceResult(
        name="EIA",
        status="ok" if oil_prices else "error",
        duration_ms=(time.time() - start) * 1000,
        data={"oil_prices": oil_prices, "signals": signals},
    )
