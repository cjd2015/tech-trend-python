"""RSS News feeds aggregation"""
import time
from .base import safe_fetch, SourceResult
import httpx


FEEDS = [
    ("http://feeds.bbci.co.uk/news/world/rss.xml", "BBC World"),
    ("https://rss.nytimes.com/services/xml/rss/nyt/World.xml", "NYT"),
    ("https://www.aljazeera.com/xml/rss/all.xml", "Al Jazeera"),
]

GEO_KEYWORDS = {
    "ukraine": (49.0, 32.0),
    "russia": (56.0, 38.0),
    "china": (35.0, 105.0),
    "iran": (32.0, 53.0),
    "israel": (31.5, 35.0),
    "gaza": (31.4, 34.4),
    "taiwan": (23.5, 121.0),
    "us": (39.0, -98.0),
}


def geo_tag(title: str) -> dict | None:
    title_lower = title.lower()
    for keyword, (lat, lon) in GEO_KEYWORDS.items():
        if keyword in title_lower:
            return {"lat": lat, "lon": lon, "region": keyword.title()}
    return {"lat": 0, "lon": 0, "region": "Global"}


def parse_rss(xml_text: str) -> list[dict]:
    items = []
    import re
    
    item_pattern = r"<item>([\s\S]*?)</item>"
    for match in re.finditer(item_pattern, xml_text):
        block = match.group(1)
        
        title_match = re.search(r"<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", block, re.DOTALL)
        link_match = re.search(r"<link>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</link>", block, re.DOTALL)
        date_match = re.search(r"<pubDate>(.*?)</pubDate>", block)
        
        if title_match:
            title = title_match.group(1).strip()
            link = link_match.group(1).strip() if link_match else ""
            date = date_match.group(1).strip() if date_match else ""
            
            if title:
                geo = geo_tag(title)
                items.append({
                    "title": title[:100],
                    "link": link,
                    "date": date,
                    **geo,
                })
    
    return items


async def fetch_news() -> SourceResult:
    start = time.time()
    all_news = []
    
    for url, source in FEEDS:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                items = parse_rss(response.text)
                for item in items:
                    item["source"] = source
                all_news.extend(items)
        except Exception:
            continue
    
    all_news.sort(key=lambda x: x.get("date", ""), reverse=True)
    
    return SourceResult(
        name="News",
        status="ok",
        duration_ms=(time.time() - start) * 1000,
        data={
            "articles": all_news[:50],
            "total": len(all_news),
        },
    )
