"""OpenSky Network - Flight tracking (no API key for limited use)"""
import time
from .base import safe_fetch, SourceResult


async def fetch_opensky() -> SourceResult:
    start = time.time()
    
    url = "https://opensky-network.org/api/states/all"
    
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url)
            
            if response.status_code == 200:
                data = response.json()
                states = data.get("states", []) or []
                
                hotspots = []
                by_country = {}
                total = len(states)
                
                for state in states:
                    icao24, callsign, origin_country, time_position, last_contact, \
                    longitude, latitude, baro_altitude, on_ground, velocity, \
                    heading, vertical_rate, sensors = state[:13]
                    
                    country = origin_country or "Unknown"
                    by_country[country] = by_country.get(country, 0) + 1
                
                top_countries = sorted(by_country.items(), key=lambda x: x[1], reverse=True)[:5]
                
                return SourceResult(
                    name="OpenSky",
                    status="ok",
                    duration_ms=(time.time() - start) * 1000,
                    data={
                        "total_aircraft": total,
                        "by_country": dict(top_countries),
                        "timestamp": data.get("time"),
                    },
                )
            else:
                return SourceResult(
                    name="OpenSky",
                    status="error",
                    duration_ms=(time.time() - start) * 1000,
                    error=f"HTTP {response.status_code}",
                )
    except Exception as e:
        return SourceResult(
            name="OpenSky",
            status="error",
            duration_ms=(time.time() - start) * 1000,
            error=str(e),
        )
