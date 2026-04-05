"""FRED - Federal Reserve Economic Data (free API key required)"""
import time
from .base import safe_fetch, SourceResult
from config import FRED_API_KEY

SERIES = {
    "VIXCLS": "VIX (Fear Index)",
    "BAMLH0A0HYM2": "High Yield Spread",
    "T10Y2Y": "10Y-2Y Spread",
    "DGS10": "10Y Yield",
    "DFF": "Fed Funds Rate",
    "UNRATE": "Unemployment",
    "CPIAUCSL": "CPI",
}


async def fetch_fred() -> SourceResult:
    start = time.time()
    
    if not FRED_API_KEY:
        return SourceResult(
            name="FRED",
            status="error",
            duration_ms=(time.time() - start) * 1000,
            error="No FRED API key. Get free at https://fred.stlouisfed.org/docs/api/api_key.html",
        )
    
    indicators = []
    signals = []
    
    for series_id, label in SERIES.items():
        url = "https://api.stlouisfed.org/fred/series/observations"
        params = {
            "series_id": series_id,
            "api_key": FRED_API_KEY,
            "file_type": "json",
            "sort_order": "desc",
            "limit": 5,
        }
        data = await safe_fetch(url, params=params)
        
        if data and "error" not in data:
            observations = data.get("observations", [])
            valid_obs = [o for o in observations if o.get("value") != "."]
            
            if valid_obs:
                latest = valid_obs[0]
                value = float(latest["value"])
                
                indicators.append({
                    "id": series_id,
                    "label": label,
                    "value": value,
                    "date": latest["date"],
                })
                
                if series_id == "VIXCLS" and value > 30:
                    signals.append(f"VIX ELEVATED at {value} - high fear/volatility")
                elif series_id == "VIXCLS" and value > 40:
                    signals.append(f"VIX EXTREME at {value} - crisis-level fear")
                elif series_id == "T10Y2Y" and value < 0:
                    signals.append("YIELD CURVE INVERTED - recession signal")
    
    return SourceResult(
        name="FRED",
        status="ok" if indicators else "error",
        duration_ms=(time.time() - start) * 1000,
        data={"indicators": indicators, "signals": signals},
    )
