"""Yahoo Finance - Live market quotes"""
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
