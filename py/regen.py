#!/usr/bin/env python3
"""Regenerate all source files"""
import os

SOURCES_INIT = '''"""Data source modules"""
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
    "gdelt", "opensky", "firms", "ships", "safecast", "acled",
    "reliefweb", "who", "ofac", "opensanctions", "adsb",
    "fred", "treasury", "bls", "eia", "gscpi", "usaspending", "comtrade",
    "noaa", "epa", "patents", "bluesky", "reddit", "telegram", "kiwisdr",
    "space", "yfinance", "cisa_kev", "cloudflare_radar",
]

SOURCE_TIMEOUT = 30.0
'''

BASE_PY = '''"""Base classes and utilities for all data sources"""
from __future__ import annotations
import asyncio
import time
from dataclasses import dataclass, field
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
    body: Optional[str] = None,
) -> Optional[Dict]:
    """Fetch JSON with timeout and error handling."""
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            if method == "POST":
                if json:
                    response = await client.post(url, headers=headers, json=json)
                elif body:
                    response = await client.post(url, headers=headers, content=body)
                else:
                    response = await client.post(url, headers=headers)
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
    """Fetch raw text content."""
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.text
    except Exception as e:
        return None


def parse_csv_lines(csv_text: str) -> List[Dict]:
    """Parse CSV text into list of dicts."""
    if not csv_text:
        return []
    lines = csv_text.strip().split("\\n")
    if len(lines) < 2:
        return []
    headers = [h.strip().strip('"') for h in lines[0].split(",")]
    result = []
    for line in lines[1:]:
        values = []
        current = ""
        in_quotes = False
        for char in line:
            if char == '"':
                in_quotes = not in_quotes
            elif char == "," and not in_quotes:
                values.append(current.strip().strip('"'))
                current = ""
            else:
                current += char
        values.append(current.strip().strip('"'))
        if len(values) == len(headers):
            row = {}
            for i, h in enumerate(headers):
                row[h.strip()] = values[i]
            result.append(row)
    return result
'''

def write_file(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Written: {path}")

def main():
    base = "crucix/sources"
    
    write_file(f"{base}/__init__.py", SOURCES_INIT)
    write_file(f"{base}/base.py", BASE_PY)
    
    # Tier 1
    tier1_init = '''"""Tier 1: Core OSINT & Geopolitical sources"""
'''
    write_file(f"{base}/tier1/__init__.py", tier1_init)
    
    # Tier 2
    tier2_init = '''"""Tier 2: Economic & Financial sources"""
'''
    write_file(f"{base}/tier2/__init__.py", tier2_init)
    
    # Tier 3
    tier3_init = '''"""Tier 3: Weather, Environment, Tech, Social, SIGINT"""
'''
    write_file(f"{base}/tier3/__init__.py", tier3_init)
    
    # Tier 4
    tier4_init = '''"""Tier 4: Space & Satellites"""
'''
    write_file(f"{base}/tier4/__init__.py", tier4_init)
    
    # Tier 5
    tier5_init = '''"""Tier 5: Live Market Data"""
'''
    write_file(f"{base}/tier5/__init__.py", tier5_init)
    
    # Tier 6
    tier6_init = '''"""Tier 6: Cyber & Infrastructure"""
'''
    write_file(f"{base}/tier6/__init__.py", tier6_init)
    
    print("Done regenerating __init__.py files")

if __name__ == "__main__":
    main()
