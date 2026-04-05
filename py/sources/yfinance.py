"""Yahoo Finance - Live market data (no API key required)"""
import time
from .base import safe_fetch, SourceResult

SYMBOLS = {
    "^GSPC": "S&P 500",
    "^IXIC": "Nasdaq",
    "^DJI": "Dow Jones",
    "GC=F": "Gold",
    "CL=F": "WTI Crude",
    "BTC-USD": "Bitcoin",
    "^VIX": "VIX",
}


async def fetch_yfinance() -> SourceResult:
    start = time.time()
    quotes = {}
    
    async def fetch_quote(symbol: str, name: str):
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        params = {"range": "5d", "interval": "1d", "includePrePost": "false"}
        
        data = await safe_fetch(url, timeout=10.0, headers=headers, params=params)
        
        if data and "error" not in data:
            result = data.get("chart", {}).get("result", [{}])[0]
            meta = result.get("meta", {})
            quote = result.get("indicators", {}).get("quote", [{}])[0]
            closes = quote.get("close", [])
            
            price = meta.get("regularMarketPrice") or (closes[-1] if closes else None)
            prev_close = meta.get("chartPreviousClose") or meta.get("previousClose")
            
            if price and prev_close:
                change = price - prev_close
                change_pct = (change / prev_close) * 100
                
                return {
                    "symbol": symbol,
                    "name": name,
                    "price": round(price, 2),
                    "change": round(change, 2),
                    "change_pct": round(change_pct, 2),
                    "history": [
                        {"date": closes[i], "close": round(closes[i], 2)}
                        for i in range(len(closes)) if closes[i] is not None
                    ],
                }
        
        return {"symbol": symbol, "name": name, "error": "fetch failed"}
    
    import asyncio
    tasks = [fetch_quote(sym, name) for sym, name in SYMBOLS.items()]
    results = await asyncio.gather(*tasks)
    
    for q in results:
        if q:
            quotes[q["symbol"]] = q
    
    return SourceResult(
        name="YFinance",
        status="ok",
        duration_ms=(time.time() - start) * 1000,
        data={
            "quotes": quotes,
            "indexes": [quotes.get(s) for s in ["^GSPC", "^IXIC", "^DJI"]],
            "commodities": [quotes.get(s) for s in ["GC=F", "CL=F"]],
            "crypto": [quotes.get(s) for s in ["BTC-USD"]],
            "vix": quotes.get("^VIX"),
        },
    )
