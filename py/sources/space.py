"""CelesTrak - Satellite tracking (no API key required)"""
import time
from .base import safe_fetch, SourceResult


async def fetch_space() -> SourceResult:
    start = time.time()
    
    url = "https://www.celestrak.org/NORAD/elements/gp.php"
    params = {
        "GROUP": "stations",
        "FORMAT": "json",
    }
    
    data = await safe_fetch(url, params=params)
    
    iss = None
    if data and isinstance(data, list) and len(data) > 0:
        sat = data[0]
        iss = {
            "name": sat.get("OBJECT_NAME", "ISS"),
            "norad_id": sat.get("NORAD_CAT_ID"),
            "epoch": sat.get("EPOCH"),
            "inclination": float(sat.get("INCLINATION", 0)),
            "period": float(sat.get("PERIOD", 92.7)),
        }
    
    constellations = {}
    
    for group in ["starlink", "oneweb"]:
        url = "https://www.celestrak.org/NORAD/elements/gp.php"
        params = {"GROUP": group, "FORMAT": "json"}
        data = await safe_fetch(url, params=params)
        
        if data and isinstance(data, list):
            constellations[group] = len(data)
    
    return SourceResult(
        name="Space",
        status="ok",
        duration_ms=(time.time() - start) * 1000,
        data={
            "iss": iss,
            "constellations": constellations,
            "signals": [],
        },
    )
