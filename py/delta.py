"""Delta Engine - Compare sweeps and detect changes"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class DeltaSignal:
    key: str
    label: str
    from_value: float
    to_value: float
    change: float
    pct_change: float
    direction: str
    severity: str


@dataclass
class DeltaResult:
    timestamp: str
    total_changes: int
    critical_changes: int
    direction: str
    signals: list[dict]
    summary: dict


THRESHOLDS = {
    "vix": 5,
    "wti": 3,
    "brent": 3,
    "gold": 2,
    "bitcoin": 5,
    "total_aircraft": 50,
    "total_detections": 500,
}

RISK_KEYS = ["vix", "high_yield_spread", "total_detections"]


def compute_delta(current: dict, previous: dict | None) -> DeltaResult | None:
    """Compare current sweep with previous to detect changes."""
    
    if not previous:
        return None
    
    signals = []
    critical = 0
    
    vix_curr = _get_vix(current)
    vix_prev = _get_vix(previous)
    
    if vix_curr is not None and vix_prev is not None:
        pct = _pct_change(vix_prev, vix_curr)
        if abs(pct) > THRESHOLDS.get("vix", 5):
            severity = _severity(pct, THRESHOLDS["vix"])
            signals.append({
                "key": "vix",
                "label": "VIX",
                "from": vix_prev,
                "to": vix_curr,
                "pct_change": pct,
                "direction": "up" if pct > 0 else "down",
                "severity": severity,
            })
            if severity == "critical":
                critical += 1
    
    wti_curr = _get_wti(current)
    wti_prev = _get_wti(previous)
    
    if wti_curr is not None and wti_prev is not None:
        pct = _pct_change(wti_prev, wti_curr)
        if abs(pct) > THRESHOLDS.get("wti", 3):
            severity = _severity(pct, THRESHOLDS["wti"])
            signals.append({
                "key": "wti",
                "label": "WTI Crude",
                "from": wti_prev,
                "to": wti_curr,
                "pct_change": pct,
                "direction": "up" if pct > 0 else "down",
                "severity": severity,
            })
    
    gold_curr = _get_gold(current)
    gold_prev = _get_gold(previous)
    
    if gold_curr is not None and gold_prev is not None:
        pct = _pct_change(gold_prev, gold_curr)
        if abs(pct) > THRESHOLDS.get("gold", 2):
            severity = _severity(pct, THRESHOLDS["gold"])
            signals.append({
                "key": "gold",
                "label": "Gold",
                "from": gold_prev,
                "to": gold_curr,
                "pct_change": pct,
                "direction": "up" if pct > 0 else "down",
                "severity": severity,
            })
    
    aircraft_curr = _get_aircraft(current)
    aircraft_prev = _get_aircraft(previous)
    
    if aircraft_curr is not None and aircraft_prev is not None:
        diff = aircraft_curr - aircraft_prev
        if abs(diff) > THRESHOLDS.get("total_aircraft", 50):
            signals.append({
                "key": "aircraft",
                "label": "Global Aircraft",
                "from": aircraft_prev,
                "to": aircraft_curr,
                "change": diff,
                "direction": "up" if diff > 0 else "down",
                "severity": "moderate",
            })
    
    fire_curr = _get_fires(current)
    fire_prev = _get_fires(previous)
    
    if fire_curr is not None and fire_prev is not None:
        diff = fire_curr - fire_prev
        if abs(diff) > THRESHOLDS.get("total_detections", 500):
            severity = "high" if abs(diff) > 2000 else "moderate"
            signals.append({
                "key": "fires",
                "label": "Fire Detections",
                "from": fire_prev,
                "to": fire_curr,
                "change": diff,
                "direction": "up" if diff > 0 else "down",
                "severity": severity,
            })
    
    direction = _calc_direction(signals)
    
    return DeltaResult(
        timestamp=current.get("timestamp", datetime.utcnow().isoformat()),
        total_changes=len(signals),
        critical_changes=critical,
        direction=direction,
        signals=signals,
        summary={
            "total": len(signals),
            "critical": critical,
            "direction": direction,
        },
    )


def _get_vix(data: dict) -> float | None:
    try:
        for ind in data.get("fred", {}).get("indicators", []):
            if ind.get("id") == "VIXCLS":
                return ind.get("value")
        for q in data.get("markets", {}).get("vix", {}).values() if isinstance(data.get("markets", {}).get("vix"), dict) else []:
            if "price" in q:
                return q["price"]
        return data.get("markets", {}).get("vix", {}).get("price")
    except:
        return None


def _get_wti(data: dict) -> float | None:
    return data.get("eia", {}).get("oil_prices", {}).get("wti", {}).get("value")


def _get_gold(data: dict) -> float | None:
    try:
        quotes = data.get("markets", {}).get("quotes", {})
        return quotes.get("GC=F", {}).get("price")
    except:
        return None


def _get_aircraft(data: dict) -> int | None:
    return data.get("opensky", {}).get("total_aircraft")


def _get_fires(data: dict) -> int | None:
    return data.get("firms", {}).get("total_detections")


def _pct_change(old: float, new: float) -> float:
    if old == 0:
        return 100 if new > 0 else 0
    return round(((new - old) / abs(old)) * 100, 2)


def _severity(pct: float, threshold: float) -> str:
    abs_pct = abs(pct)
    if abs_pct > threshold * 3:
        return "critical"
    elif abs_pct > threshold * 2:
        return "high"
    return "moderate"


def _calc_direction(signals: list[dict]) -> str:
    risk_up = 0
    risk_down = 0
    
    for s in signals:
        if s.get("key") in RISK_KEYS:
            if s.get("direction") == "up":
                risk_up += 1
            else:
                risk_down += 1
    
    if risk_up > risk_down + 1:
        return "risk-off"
    elif risk_down > risk_up + 1:
        return "risk-on"
    return "mixed"
