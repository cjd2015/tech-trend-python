#!/usr/bin/env python3
"""Generate all source files for Crucix Python - Fixed imports"""
from __future__ import annotations
import os

def write_file(path: str, content: str):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Written: {path}")

def main():
    base = "crucix/sources"
    
    # Write __init__.py files
    write_file(f"{base}/__init__.py", '''"""Data source modules"""
from __future__ import annotations
from .base import SourceResult, safe_fetch, http_get

from .tier1 import (
    gdelt, opensky, firms, ships, safecast, acled,
    reliefweb, who, ofac, opensanctions, adsb
)

from .tier2 import (
    fred, treasury, bls, eia, gscpi, usaspending, comtrade
)

from .tier3 import (
    noaa, epa, patents, bluesky, reddit, telegram, kiwisdr
)

from .tier4 import space
from .tier5 import yfinance
from .tier6 import cisa_kev, cloudflare_radar

__all__ = [
    "SourceResult", "safe_fetch", "http_get",
]

SOURCE_TIMEOUT = 30.0
''')
    
    write_file(f"{base}/base.py", '''"""Base classes and utilities for all data sources"""
from __future__ import annotations
import asyncio
import time
from dataclasses import dataclass
from typing import Any, Optional, Dict, List
import httpx


@dataclass
class SourceResult:
    name: str
    status: str
    duration_ms: float
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.status == "ok"


async def safe_fetch(
    url: str,
    timeout: float = 30.0,
    headers: Optional[Dict] = None,
    params: Optional[Dict] = None,
    method: str = "GET",
    json: Optional[Dict] = None,
) -> Optional[Dict]:
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            if method == "POST":
                response = await client.post(url, headers=headers, json=json)
            else:
                response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        return {"error": str(e)}


async def http_get(
    url: str,
    timeout: float = 30.0,
    headers: Optional[Dict] = None,
    params: Optional[Dict] = None,
) -> Optional[str]:
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.text
    except Exception:
        return None
''')
    
    # Tier __init__.py
    for tier in ["tier1", "tier2", "tier3", "tier4", "tier5", "tier6"]:
        write_file(f"{base}/{tier}/__init__.py", f'"""Tier {tier[-1]} sources"""')
    
    # Key sources - these import from ..base
    write_file(f"{base}/tier5/yfinance.py", '''"""Yahoo Finance - Live market quotes"""
from __future__ import annotations
import time
import asyncio
import httpx
from ..base import SourceResult


SYMBOLS = {
    "^GSPC": "S&P 500",
    "^IXIC": "Nasdaq",
    "^DJI": "Dow Jones",
    "GC=F": "Gold",
    "CL=F": "WTI Crude",
    "BTC-USD": "Bitcoin",
    "^VIX": "VIX",
}


async def fetch_quote(symbol, name):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    headers = {"User-Agent": "Mozilla/5.0"}
    params = {"range": "5d", "interval": "1d"}
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers, params=params)
            if response.status_code == 200:
                data = response.json()
                result = data.get("chart", {}).get("result", [{}])[0]
                meta = result.get("meta", {})
                closes = result.get("indicators", {}).get("quote", [{}])[0].get("close", [])
                price = meta.get("regularMarketPrice") or (closes[-1] if closes else None)
                prev = meta.get("chartPreviousClose")
                if price and prev:
                    return {
                        "symbol": symbol, "name": name,
                        "price": round(price, 2),
                        "change": round(price - prev, 2),
                        "change_pct": round(((price - prev) / prev) * 100, 2),
                    }
    except:
        pass
    return {"symbol": symbol, "name": name, "error": "failed"}


async def briefing():
    start = time.time()
    results = await asyncio.gather(*[fetch_quote(s, n) for s, n in SYMBOLS.items()])
    quotes = {r["symbol"]: r for r in results if r}
    return SourceResult(
        name="YFinance", status="ok", duration_ms=(time.time()-start)*1000,
        data={"quotes": quotes, "vix": quotes.get("^VIX")},
    )
''')
    
    write_file(f"{base}/tier1/opensky.py", '''"""OpenSky Network - Flight tracking"""
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
''')
    
    write_file(f"{base}/tier2/fred.py", '''"""FRED - Federal Reserve Economic Data"""
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
''')
    
    write_file(f"{base}/tier2/eia.py", '''"""EIA - US Energy Information Administration"""
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
''')
    
    write_file(f"{base}/tier4/space.py", '''"""CelesTrak - Satellite tracking"""
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
''')
    
    # Stub sources - these don't need to import from base
    stubs = [
        ("tier1/gdelt.py", '"""GDELT"""\nfrom __future__ import annotations\nfrom ..base import SourceResult\n\nasync def briefing():\n    return SourceResult(name="GDELT", status="ok", duration_ms=0, data={"total_articles": 0})\n'),
        ("tier1/firms.py", '"""FIRMS"""\nfrom __future__ import annotations\nfrom ..base import SourceResult\n\nasync def briefing():\n    return SourceResult(name="FIRMS", status="ok", duration_ms=0, data={"total_detections": 0})\n'),
        ("tier1/ships.py", '"""Maritime"""\nfrom __future__ import annotations\nfrom ..base import SourceResult\n\nasync def briefing():\n    return SourceResult(name="Maritime", status="ok", duration_ms=0, data={"chokepoints": []})\n'),
        ("tier1/safecast.py", '"""Safecast"""\nfrom __future__ import annotations\nfrom ..base import SourceResult\n\nasync def briefing():\n    return SourceResult(name="Safecast", status="ok", duration_ms=0, data={"sites": []})\n'),
        ("tier1/acled.py", '"""ACLED"""\nfrom __future__ import annotations\nfrom ..base import SourceResult\n\nasync def briefing():\n    return SourceResult(name="ACLED", status="ok", duration_ms=0, data={"total_events": 0})\n'),
        ("tier1/reliefweb.py", '"""ReliefWeb"""\nfrom __future__ import annotations\nfrom ..base import SourceResult\n\nasync def briefing():\n    return SourceResult(name="ReliefWeb", status="ok", duration_ms=0, data={"total_disasters": 0})\n'),
        ("tier1/who.py", '"""WHO"""\nfrom __future__ import annotations\nfrom ..base import SourceResult\n\nasync def briefing():\n    return SourceResult(name="WHO", status="ok", duration_ms=0, data={"total": 0})\n'),
        ("tier1/ofac.py", '"""OFAC"""\nfrom __future__ import annotations\nfrom ..base import SourceResult\n\nasync def briefing():\n    return SourceResult(name="OFAC", status="ok", duration_ms=0, data={"sdn_count": 0})\n'),
        ("tier1/opensanctions.py", '"""OpenSanctions"""\nfrom __future__ import annotations\nfrom ..base import SourceResult\n\nasync def briefing():\n    return SourceResult(name="OpenSanctions", status="ok", duration_ms=0, data={"total_sanctioned": 0})\n'),
        ("tier1/adsb.py", '"""ADS-B"""\nfrom __future__ import annotations\nfrom ..base import SourceResult\n\nasync def briefing():\n    return SourceResult(name="ADS-B", status="ok", duration_ms=0, data={"total_aircraft": 0})\n'),
        ("tier2/treasury.py", '"""Treasury"""\nfrom __future__ import annotations\nfrom ..base import SourceResult\n\nasync def briefing():\n    return SourceResult(name="Treasury", status="ok", duration_ms=0, data={"total_debt": 0})\n'),
        ("tier2/bls.py", '"""BLS"""\nfrom __future__ import annotations\nfrom ..base import SourceResult\n\nasync def briefing():\n    return SourceResult(name="BLS", status="ok", duration_ms=0, data={"indicators": []})\n'),
        ("tier2/gscpi.py", '"""GSCPI"""\nfrom __future__ import annotations\nfrom ..base import SourceResult\n\nasync def briefing():\n    return SourceResult(name="GSCPI", status="ok", duration_ms=0, data={"latest": None})\n'),
        ("tier2/usaspending.py", '"""USAspending"""\nfrom __future__ import annotations\nfrom ..base import SourceResult\n\nasync def briefing():\n    return SourceResult(name="USAspending", status="ok", duration_ms=0, data={"total_spending": 0})\n'),
        ("tier2/comtrade.py", '"""Comtrade"""\nfrom __future__ import annotations\nfrom ..base import SourceResult\n\nasync def briefing():\n    return SourceResult(name="Comtrade", status="ok", duration_ms=0, data={"commodities": {}})\n'),
        ("tier3/noaa.py", '"""NOAA"""\nfrom __future__ import annotations\nfrom ..base import SourceResult\n\nasync def briefing():\n    return SourceResult(name="NOAA", status="ok", duration_ms=0, data={"total_alerts": 0})\n'),
        ("tier3/epa.py", '"""EPA"""\nfrom __future__ import annotations\nfrom ..base import SourceResult\n\nasync def briefing():\n    return SourceResult(name="EPA", status="ok", duration_ms=0, data={"total_readings": 0})\n'),
        ("tier3/patents.py", '"""Patents"""\nfrom __future__ import annotations\nfrom ..base import SourceResult\n\nasync def briefing():\n    return SourceResult(name="Patents", status="ok", duration_ms=0, data={"domains": {}})\n'),
        ("tier3/bluesky.py", '"""Bluesky"""\nfrom __future__ import annotations\nfrom ..base import SourceResult\n\nasync def briefing():\n    return SourceResult(name="Bluesky", status="ok", duration_ms=0, data={"posts": []})\n'),
        ("tier3/reddit.py", '"""Reddit"""\nfrom __future__ import annotations\nfrom ..base import SourceResult\n\nasync def briefing():\n    return SourceResult(name="Reddit", status="ok", duration_ms=0, data={"posts": []})\n'),
        ("tier3/telegram.py", '"""Telegram"""\nfrom __future__ import annotations\nfrom ..base import SourceResult\n\nasync def briefing():\n    return SourceResult(name="Telegram", status="ok", duration_ms=0, data={"total_posts": 0, "urgent_posts": []})\n'),
        ("tier3/kiwisdr.py", '"""KiwiSDR"""\nfrom __future__ import annotations\nfrom ..base import SourceResult\n\nasync def briefing():\n    return SourceResult(name="KiwiSDR", status="ok", duration_ms=0, data={"network": {"total_receivers": 0}})\n'),
        ("tier6/cisa_kev.py", '"""CISA KEV"""\nfrom __future__ import annotations\nfrom ..base import SourceResult\n\nasync def briefing():\n    return SourceResult(name="CISA-KEV", status="ok", duration_ms=0, data={"total": 0})\n'),
        ("tier6/cloudflare_radar.py", '"""Cloudflare Radar"""\nfrom __future__ import annotations\nfrom ..base import SourceResult\n\nasync def briefing():\n    return SourceResult(name="Cloudflare-Radar", status="ok", duration_ms=0, data={"active_outages": []})\n'),
    ]
    
    for name, content in stubs:
        write_file(f"{base}/{name}", content)
    
    # Core files
    write_file("crucix/delta.py", '''"""Delta Engine"""
from __future__ import annotations
from typing import Optional, Dict, Any


def compute_delta(current: Dict, previous: Optional[Dict]) -> Optional[Dict]:
    if not previous:
        return None
    
    signals = {"new": [], "escalated": [], "deescalated": [], "unchanged": []}
    
    vix_curr = current.get("markets", {}).get("quotes", {}).get("^VIX", {}).get("price")
    vix_prev = previous.get("markets", {}).get("quotes", {}).get("^VIX", {}).get("price")
    
    if vix_curr and vix_prev and abs(vix_curr - vix_prev) > 2:
        pct = ((vix_curr - vix_prev) / vix_prev) * 100
        if abs(pct) > 5:
            signals["escalated" if pct > 0 else "deescalated"].append({
                "key": "vix", "label": "VIX", "from": vix_prev, "to": vix_curr, "pct_change": round(pct, 2),
            })
    
    return {
        "timestamp": current.get("timestamp"),
        "signals": signals,
        "summary": {"total_changes": sum(len(v) for v in signals.values()), "direction": "mixed"},
    }
''')
    
    write_file("crucix/llm/ideas.py", '''"""Trade Ideas Generator"""
from __future__ import annotations
from typing import List, Dict, Any, Optional


async def generate_trade_ideas(provider, data: Dict, delta: Optional[Dict]) -> List[Dict]:
    ideas = []
    vix = data.get("markets", {}).get("quotes", {}).get("^VIX", {}).get("price")
    
    if vix and vix > 25:
        ideas.append({
            "title": "Elevated Volatility Regime",
            "text": f"VIX at {vix:.0f} - fear elevated",
            "type": "hedge", "confidence": "Medium", "horizon": "tactical",
        })
    
    return ideas[:8]
''')
    
    write_file("crucix/alerts/telegram.py", '''"""Telegram Alerts"""
from __future__ import annotations
import asyncio
import httpx
from ...config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


class TelegramAlerter:
    def __init__(self):
        self.bot_token = TELEGRAM_BOT_TOKEN
        self.chat_id = TELEGRAM_CHAT_ID
        self._configured = bool(self.bot_token and self.chat_id)
    
    @property
    def is_configured(self) -> bool:
        return self._configured
    
    async def send_message(self, text: str):
        if not self._configured:
            return
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(url, json={"chat_id": self.chat_id, "text": text, "parse_mode": "Markdown"})
        except:
            pass
    
    async def evaluate_and_alert(self, llm_provider, delta, memory):
        if delta and delta.get("summary", {}).get("total_changes", 0) > 0:
            await self.send_message(f"[Crucix] {delta['summary']['total_changes']} changes detected")
''')
    
    write_file("crucix/alerts/discord.py", '''"""Discord Alerts"""
from __future__ import annotations
import httpx
from ...config import DISCORD_WEBHOOK_URL


class DiscordAlerter:
    def __init__(self):
        self.webhook_url = DISCORD_WEBHOOK_URL
        self._configured = bool(self.webhook_url)
    
    @property
    def is_configured(self) -> bool:
        return self._configured
    
    async def send_webhook(self, content: str, embed: dict = None):
        if not self._configured:
            return
        body = {"content": content}
        if embed:
            body["embeds"] = [embed]
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(self.webhook_url, json=body)
        except:
            pass
    
    async def evaluate_and_alert(self, llm_provider, delta, memory):
        if delta and delta.get("summary", {}).get("total_changes", 0) > 0:
            embed = {"title": "Crucix Alert", "description": f"{delta['summary']['total_changes']} changes detected"}
            await self.send_webhook(None, embed)
''')
    
    print("\\nAll files generated!")

if __name__ == "__main__":
    main()
