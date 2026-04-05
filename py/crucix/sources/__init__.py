"""Data source modules"""
from __future__ import annotations
from .base import SourceResult, safe_fetch, http_get

from .tier1 import (
    gdelt, opensky, firms, ships, safecast, acled,
    reliefweb, who, ofac, opensanctions, adsb
)

from .tier2 import (
    treasury, gscpi, usaspending, comtrade
)

from .tier3 import (
    noaa, epa, patents, bluesky, reddit, telegram, kiwisdr
)

from .tier4 import space
from .tier5 import yfinance
from .tier6 import cisa_kev, cloudflare_radar
from . import tech

__all__ = [
    "SourceResult", "safe_fetch", "http_get",
]

SOURCE_TIMEOUT = 30.0
