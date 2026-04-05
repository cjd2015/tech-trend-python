"""NASA FIRMS - Fire/thermal anomaly detection (free API key)"""
import time
from .base import safe_fetch, SourceResult
from config import FIRMS_MAP_KEY

REGIONS = {
    "world": "WORLD",
    "europe": "EUROPE",
    "asia": "ASIA",
    "middle_east": "MIDDLE_EAST",
    "africa": "AFRICA",
    "south_america": "SOUTH_AMERICA",
}


async def fetch_firms() -> SourceResult:
    start = time.time()
    
    if not FIRMS_MAP_KEY:
        return SourceResult(
            name="FIRMS",
            status="error",
            duration_ms=(time.time() - start) * 1000,
            error="No FIRMS MAP key. Get free at https://firms.modaps.eosdis.nasa.gov/api/area/",
        )
    
    hotspots = []
    total_detections = 0
    
    for region_name, region_code in REGIONS.items():
        url = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"
        params = {
            "key": FIRMS_MAP_KEY,
            "source": "VIIRS_SNPP_NRT",
            "area": region_code,
        }
        
        headers = {"Accept": "text/csv"}
        
        try:
            import httpx
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params, headers=headers)
                
                if response.status_code == 200:
                    lines = response.text.strip().split("\n")
                    count = len(lines) - 1
                    total_detections += count
                    
                    if count > 0:
                        hotspots.append({
                            "region": region_name,
                            "detections": count,
                        })
        except Exception:
            continue
    
    signals = []
    if total_detections > 50000:
        signals.append(f"ELEVATED fire activity: {total_detections:,} global detections")
    
    return SourceResult(
        name="FIRMS",
        status="ok",
        duration_ms=(time.time() - start) * 1000,
        data={
            "total_detections": total_detections,
            "hotspots": hotspots,
            "signals": signals,
        },
    )
