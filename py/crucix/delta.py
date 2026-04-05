"""Delta Engine - Compare two sweeps and produce structured changes"""
from __future__ import annotations
import hashlib
from typing import Optional, Dict, Any, List


NUMERIC_THRESHOLDS = {
    "vix": 5,
    "hy_spread": 5,
    "10y2y": 10,
    "wti": 3,
    "brent": 3,
    "natgas": 5,
    "gold": 2,
    "silver": 3,
    "unemployment": 2,
    "fed_funds": 1,
    "10y_yield": 3,
    "usd_index": 1,
    "mortgage": 2,
}

COUNT_THRESHOLDS = {
    "urgent_posts": 2,
    "thermal_total": 500,
    "air_total": 50,
    "who_alerts": 1,
    "conflict_events": 5,
    "conflict_fatalities": 10,
    "sdr_online": 3,
    "news_count": 5,
    "sources_ok": 1,
}

NUMERIC_METRICS = [
    {"key": "vix", "path": ["fred"], "id": "VIXCLS", "label": "VIX"},
    {"key": "hy_spread", "path": ["fred"], "id": "BAMLH0A0HYM2", "label": "HY Spread"},
    {"key": "10y2y", "path": ["fred"], "id": "T10Y2Y", "label": "10Y-2Y Spread"},
    {"key": "wti", "path": ["energy"], "key2": "wti", "label": "WTI Crude"},
    {"key": "brent", "path": ["energy"], "key2": "brent", "label": "Brent Crude"},
    {"key": "natgas", "path": ["energy"], "key2": "natgas", "label": "Natural Gas"},
    {"key": "gold", "path": ["markets"], "key2": "gold", "label": "Gold"},
    {"key": "silver", "path": ["markets"], "key2": "silver", "label": "Silver"},
    {"key": "unemployment", "path": ["fred"], "id": "LNS14000000", "label": "Unemployment"},
    {"key": "fed_funds", "path": ["fred"], "id": "DFF", "label": "Fed Funds Rate"},
    {"key": "10y_yield", "path": ["fred"], "id": "DGS10", "label": "10Y Yield"},
    {"key": "usd_index", "path": ["fred"], "id": "DTWEXBGS", "label": "USD Index"},
    {"key": "mortgage", "path": ["fred"], "id": "MORTGAGE30US", "label": "30Y Mortgage"},
]

COUNT_METRICS = [
    {"key": "urgent_posts", "path": ["telegram"], "key2": "urgent", "label": "Urgent OSINT Posts"},
    {"key": "thermal_total", "path": ["firms"], "key2": "total", "label": "Thermal Detections"},
    {"key": "air_total", "path": ["opensky"], "key2": "total", "label": "Air Activity"},
    {"key": "who_alerts", "path": ["who"], "key2": "length", "label": "WHO Alerts"},
    {"key": "conflict_events", "path": ["acled"], "key2": "totalEvents", "label": "Conflict Events"},
    {"key": "conflict_fatalities", "path": ["acled"], "key2": "totalFatalities", "label": "Conflict Fatalities"},
    {"key": "news_count", "path": ["news"], "key2": "count", "label": "News Items"},
    {"key": "sources_ok", "path": ["meta"], "key2": "sources_ok", "label": "Sources OK"},
]

RISK_KEYS = ["vix", "hy_spread", "urgent_posts", "conflict_events", "thermal_total"]


def _extract_numeric(data: dict, metric: dict) -> Optional[float]:
    source = data
    for p in metric.get("path", []):
        source = source.get(p, {})
    if "id" in metric:
        for item in source if isinstance(source, list) else []:
            if item.get("id") == metric["id"]:
                return item.get("value")
    elif "key2" in metric:
        return source.get(metric["key2"])
    return None


def _extract_count(data: dict, metric: dict) -> int:
    source = data
    for p in metric.get("path", []):
        source = source.get(p, {})
    if "key2" in metric:
        val = source.get(metric["key2"])
        if isinstance(val, list):
            return len(val)
        return val or 0
    if isinstance(source, list):
        return len(source)
    return source if isinstance(source, int) else 0


def _content_hash(text: str) -> str:
    if not text:
        return ""
    normalized = (
        text.lower()
        .replace(r"\d{1,2}:\d{2}(:\d{2})?", "N")
        .replace(r"\d+", "N")
        .replace(r"[^\w\s]", "")
        .replace(r"\s+", " ")
        .strip()[:100]
    )
    return hashlib.sha256(normalized.encode()).hexdigest()[:12]


def stable_post_key(post: dict) -> str:
    if not post:
        return ""
    source_id = post.get("postId") or post.get("messageId") or ""
    channel_id = post.get("channel") or post.get("chat") or ""
    date = post.get("date") or ""
    text = (post.get("text") or "").strip()[:200]
    
    if source_id:
        return f"id:{source_id}"
    if channel_id and date:
        return hashlib.sha256(f"{channel_id}|{date}|{text}".encode()).hexdigest()[:16]
    return f"semantic:{_content_hash(post.get('text', ''))}"


def compute_delta(current: dict, previous: Optional[dict], prior_runs: Optional[List[dict]] = None) -> Optional[dict]:
    if not previous or not current:
        return None
    
    signals = {"new": [], "escalated": [], "deescalated": [], "unchanged": []}
    critical_changes = 0
    
    for m in NUMERIC_METRICS:
        curr = _extract_numeric(current, m)
        prev = _extract_numeric(previous, m)
        if curr is None or prev is None:
            continue
        
        threshold = NUMERIC_THRESHOLDS.get(m["key"], 5)
        if prev != 0:
            pct_change = ((curr - prev) / abs(prev)) * 100
        else:
            pct_change = 0
        
        if abs(pct_change) > threshold:
            severity = "critical" if abs(pct_change) > threshold * 3 else "high" if abs(pct_change) > threshold * 2 else "moderate"
            entry = {
                "key": m["key"],
                "label": m["label"],
                "from": prev,
                "to": curr,
                "pctChange": round(pct_change, 2),
                "direction": "up" if pct_change > 0 else "down",
                "severity": severity,
            }
            signals["escalated" if pct_change > 0 else "deescalated"].append(entry)
            if abs(pct_change) > 10:
                critical_changes += 1
        else:
            signals["unchanged"].append(m["key"])
    
    for m in COUNT_METRICS:
        curr = _extract_count(current, m)
        prev = _extract_count(previous, m)
        diff = curr - prev
        threshold = COUNT_THRESHOLDS.get(m["key"], 1)
        
        if abs(diff) >= threshold:
            pct_change = (diff / prev * 100) if prev > 0 else (100 if diff > 0 else 0)
            severity = "critical" if abs(diff) >= threshold * 5 else "high" if abs(diff) >= threshold * 2 else "moderate"
            entry = {
                "key": m["key"],
                "label": m["label"],
                "from": prev,
                "to": curr,
                "change": diff,
                "direction": "up" if diff > 0 else "down",
                "pctChange": round(pct_change, 1),
                "severity": severity,
            }
            signals["escalated" if diff > 0 else "deescalated"].append(entry)
            if severity == "critical":
                critical_changes += 1
        else:
            signals["unchanged"].append(m["key"])
    
    prior_hashes = set()
    sources = prior_runs if prior_runs else [previous]
    for run in sources:
        tg = run.get("telegram", {})
        if isinstance(tg, dict):
            urgent = tg.get("urgent", [])
            if isinstance(urgent, list):
                for post in urgent:
                    h = stable_post_key(post)
                    if h:
                        prior_hashes.add(h)
    
    current_tg = current.get("telegram", {})
    if isinstance(current_tg, dict):
        current_urgent = current_tg.get("urgent", [])
        if isinstance(current_urgent, list):
            for post in current_urgent:
                h = stable_post_key(post)
                if h and h not in prior_hashes:
                    signals["new"].append({
                        "key": f"tg_urgent:{h}",
                        "text": post.get("text"),
                        "item": post,
                        "reason": "New urgent OSINT post",
                    })
                    critical_changes += 1
    
    curr_nuke = any(n.get("anom", False) for n in current.get("safecast", [])) if isinstance(current.get("safecast"), list) else False
    prev_nuke = any(n.get("anom", False) for n in previous.get("safecast", [])) if isinstance(previous.get("safecast"), list) else False
    
    if curr_nuke and not prev_nuke:
        signals["new"].append({"key": "nuke_anomaly", "reason": "Nuclear anomaly detected", "severity": "critical"})
        critical_changes += 5
    elif not curr_nuke and prev_nuke:
        signals["deescalated"].append({"key": "nuke_anomaly", "label": "Nuclear Anomaly", "direction": "resolved", "severity": "high"})
    
    direction = "mixed"
    risk_up = sum(1 for s in signals["escalated"] if s.get("key") in RISK_KEYS)
    risk_down = sum(1 for s in signals["deescalated"] if s.get("key") in RISK_KEYS)
    
    if risk_down > risk_up + 1:
        direction = "risk-on"
    elif risk_up > risk_down + 1:
        direction = "risk-off"
    
    return {
        "timestamp": current.get("timestamp") or current.get("meta", {}).get("timestamp"),
        "previous": previous.get("meta", {}).get("timestamp"),
        "signals": signals,
        "summary": {
            "totalChanges": len(signals["new"]) + len(signals["escalated"]) + len(signals["deescalated"]),
            "criticalChanges": critical_changes,
            "direction": direction,
            "signalBreakdown": {
                "new": len(signals["new"]),
                "escalated": len(signals["escalated"]),
                "deescalated": len(signals["deescalated"]),
                "unchanged": len(signals["unchanged"]),
            },
        },
    }