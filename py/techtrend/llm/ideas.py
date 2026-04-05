"""Trade Ideas Generator"""
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
