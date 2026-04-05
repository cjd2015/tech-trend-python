"""Discord Alerts - Multi-tier alerts with webhook support"""
from __future__ import annotations
import asyncio
import hashlib
import httpx
import json
from typing import Optional, Dict, Any, List
from ..config import DISCORD_BOT_TOKEN, DISCORD_CHANNEL_ID, DISCORD_GUILD_ID, DISCORD_WEBHOOK_URL


TIER_CONFIG = {
    "FLASH": {"color": 0xFF0000, "label": "FLASH", "cooldown_ms": 5 * 60 * 1000, "max_per_hour": 6},
    "PRIORITY": {"color": 0xFFAA00, "label": "PRIORITY", "cooldown_ms": 30 * 60 * 1000, "max_per_hour": 4},
    "ROUTINE": {"color": 0x3498DB, "label": "ROUTINE", "cooldown_ms": 60 * 60 * 1000, "max_per_hour": 2},
}


class DiscordAlerter:
    def __init__(self):
        self.bot_token = DISCORD_BOT_TOKEN
        self.channel_id = DISCORD_CHANNEL_ID
        self.guild_id = DISCORD_GUILD_ID
        self.webhook_url = DISCORD_WEBHOOK_URL
        self._configured = bool(self.bot_token and self.channel_id) or bool(self.webhook_url)
        self._alert_history: List[Dict] = []
        self._content_hashes: Dict[str, str] = {}
        self._mute_until: Optional[int] = None
        self._command_handlers: Dict[str, Any] = {}
        self._client = None
        self._ready = False

    @property
    def is_configured(self) -> bool:
        return self._configured

    async def send_webhook(self, content: str = None, embed: dict = None):
        if not self._configured:
            return False
        body = {"content": content} if content else {}
        if embed:
            body["embeds"] = [embed]
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(self.webhook_url or "", json=body)
                return response.status_code in (200, 204)
        except Exception:
            return False

    def _content_hash(self, signal: Dict) -> str:
        content = signal.get("text", "") or signal.get("label", "") or signal.get("key", "")
        content = content.lower()[:120]
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _record_content_hash(self, signal: Dict):
        h = self._content_hash(signal)
        from datetime import datetime
        self._content_hashes[h] = datetime.now().isoformat()

    def _is_semantic_duplicate(self, signal: Dict) -> bool:
        h = self._content_hash(signal)
        last_seen = self._content_hashes.get(h)
        if not last_seen:
            return False
        from datetime import datetime, timedelta
        try:
            last_time = datetime.fromisoformat(last_seen).timestamp()
            return datetime.now().timestamp() - last_time < 4 * 3600
        except:
            return False

    def _check_rate_limit(self, tier: str) -> bool:
        config = TIER_CONFIG.get(tier)
        if not config:
            return True
        from time import time
        now = time() * 1000
        last_same = next((a for a in reversed(self._alert_history) if a.get("tier") == tier), None)
        if last_same and (now - last_same.get("timestamp", 0)) < config["cooldown_ms"]:
            return False
        one_hour_ago = now - 3600 * 1000
        recent = sum(1 for a in self._alert_history if a.get("tier") == tier and a.get("timestamp", 0) > one_hour_ago)
        return recent < config["max_per_hour"]

    def _record_alert(self, tier: str):
        from time import time
        self._alert_history.append({"tier": tier, "timestamp": time() * 1000})
        if len(self._alert_history) > 50:
            self._alert_history = self._alert_history[-50:]

    def _is_muted(self) -> bool:
        if not self._mute_until:
            return False
        from time import time
        if time() * 1000 > self._mute_until:
            self._mute_until = None
            return False
        return True

    def on_command(self, command: str, handler):
        self._command_handlers[command.lower()] = handler

    async def start(self):
        if not self._configured:
            return
        print("[Discord] Bot enabled (webhook mode)")

    async def stop(self):
        if self._client:
            self._client = None
            self._ready = False

    async def evaluate_and_alert(self, llm_provider, delta: Optional[Dict], memory):
        if not self._configured:
            return False
        if not delta or not delta.get("summary", {}).get("totalChanges"):
            return False
        if self._is_muted():
            return False

        all_signals = (delta.get("signals", {}).get("new", []) or []) + (delta.get("signals", {}).get("escalated", []) or [])
        new_signals = [s for s in all_signals if not self._is_semantic_duplicate(s)]

        if not new_signals:
            return False

        evaluation = self._rule_based_evaluation(new_signals, delta)

        if not evaluation or not evaluation.get("shouldAlert"):
            return False

        tier = evaluation.get("tier", "ROUTINE")
        if not self._check_rate_limit(tier):
            return False

        embed = self._format_embed(evaluation, delta, tier)
        sent = await self.send_webhook(None, embed)

        if sent:
            for s in new_signals:
                self._record_content_hash(s)
            self._record_alert(tier)

        return sent

    def _rule_based_evaluation(self, signals: List[Dict], delta: Dict) -> Optional[Dict]:
        criticals = [s for s in signals if s.get("severity") == "critical"]
        highs = [s for s in signals if s.get("severity") == "high"]
        nuke_signal = next((s for s in signals if s.get("key") == "nuke_anomaly"), None)
        osint_new = [s for s in signals if s.get("key", "").startswith("tg_urgent")]
        market_keys = ["vix", "hy_spread", "wti", "brent", "natgas", "gold", "silver", "10y2y"]
        market_signals = [s for s in signals if s.get("key") in market_keys]
        conflict_keys = ["conflict_events", "conflict_fatalities", "thermal_total"]
        conflict_signals = [s for s in signals if s.get("key") in conflict_keys]

        if nuke_signal:
            return {
                "shouldAlert": True, "tier": "FLASH", "confidence": "HIGH",
                "headline": "Nuclear Anomaly Detected",
                "reason": "Safecast radiation monitors have flagged an anomaly.",
                "actionable": "Check dashboard for affected sites.",
                "signals": ["nuke_anomaly"],
            }

        has_critical_market = any(s in market_signals for s in criticals)
        has_critical_conflict = any(s in conflict_signals for s in criticals) or any(s in osint_new for s in criticals)
        if len(criticals) >= 2 and has_critical_market and has_critical_conflict:
            return {
                "shouldAlert": True, "tier": "FLASH", "confidence": "HIGH",
                "headline": f"{len(criticals)} Critical Cross-Domain Signals",
                "reason": f"{len(criticals)} critical signals across market and conflict domains.",
                "actionable": "Review dashboard immediately.",
                "signals": [s.get("label", s.get("key")) for s in criticals[:5]],
            }

        escalated_highs = [s for s in (*criticals, *highs) if s.get("direction") == "up"]
        if len(escalated_highs) >= 2:
            return {
                "shouldAlert": True, "tier": "PRIORITY", "confidence": "MEDIUM",
                "headline": f"{len(escalated_highs)} Escalating Signals",
                "reason": "Multiple indicators escalating in the same direction.",
                "actionable": "Monitor for continuation.",
                "signals": [s.get("label", s.get("key")) for s in escalated_highs[:3]],
            }

        if len(osint_new) >= 5:
            return {
                "shouldAlert": True, "tier": "PRIORITY", "confidence": "MEDIUM",
                "headline": f"OSINT Surge: {len(osint_new)} New Urgent Posts",
                "reason": f"{len(osint_new)} new urgent OSINT signals detected.",
                "actionable": "Review OSINT stream for patterns.",
                "signals": [s.get("text", s.get("key"))[:60] for s in osint_new[:5]],
            }

        if len(criticals) >= 1 or len(highs) >= 3:
            top = criticals[0] if criticals else highs[0]
            return {
                "shouldAlert": True, "tier": "ROUTINE", "confidence": "LOW",
                "headline": top.get("label", top.get("reason", "Signal Change Detected")),
                "reason": f"{len(criticals)} critical, {len(highs)} high-severity signals.",
                "actionable": "Monitor",
                "signals": [s.get("label", s.get("key")) for s in (*criticals, *highs)[:4]],
            }

        return {"shouldAlert": False, "reason": "No signals meet alert threshold"}

    def _format_embed(self, evaluation: Dict, delta: Dict, tier: str) -> dict:
        tc = TIER_CONFIG.get(tier, {})
        direction = delta.get("summary", {}).get("direction", "mixed").upper()
        direction_emoji = {"RISK-OFF": "📉", "RISK-ON": "📈", "MIXED": "↔️"}.get(direction, "↔️")

        fields = [
            {"name": "Direction", "value": f"{direction_emoji} {direction}", "inline": True},
            {"name": "Confidence", "value": evaluation.get("confidence", "MEDIUM"), "inline": True},
        ]

        if evaluation.get("actionable"):
            fields.append({"name": "Action", "value": evaluation["actionable"], "inline": False})

        if evaluation.get("signals"):
            signals_str = "\n".join(f"• {s}" for s in evaluation["signals"][:5])
            fields.append({"name": "Signals", "value": signals_str, "inline": False})

        from datetime import datetime
        return {
            "title": f"{tc.get('emoji', '⚪')} TechTrend {tc.get('label', 'ALERT')}",
            "description": f"**{evaluation.get('headline', 'Alert')}**\n{evaluation.get('reason', '')}",
            "color": tc.get("color", 0x3498DB),
            "fields": fields,
            "footer": {"text": datetime.utcnow().isoformat().replace("T", " ")[:19] + " UTC"},
        }