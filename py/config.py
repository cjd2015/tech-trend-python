import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent.parent
load_dotenv(BASE_DIR / ".env")

FRED_API_KEY = os.getenv("FRED_API_KEY")
EIA_API_KEY = os.getenv("EIA_API_KEY")
FIRMS_MAP_KEY = os.getenv("FIRMS_MAP_KEY")

REFRESH_INTERVAL_MINUTES = int(os.getenv("REFRESH_INTERVAL_MINUTES", "15"))
PORT = int(os.getenv("PORT", "3117"))
