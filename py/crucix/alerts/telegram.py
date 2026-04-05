"""Telegram Alerts - Multi-tier alerts with bot commands"""
from __future__ import annotations
import asyncio
import hashlib
import httpx
import json
from typing import Optional, Callable, Dict, Any, List
from ..config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_POLLING_INTERVAL


TIER_CONFIG = {
    "FLASH": {"emoji": "🔴", "label": "FLASH", "cooldown_ms": 5 * 60 * 1000, "max_per_hour": 6},
    "PRIORITY": {"emoji": "🟡", "label": "PRIORITY", "cooldown_ms": 30 * 60 * 1000, "max_per_hour": 4},
    "ROUTINE": {"emoji": "🔵", "label": "ROUTINE", "cooldown_ms": 60 * 60 * 1000, "max_per_hour": 2},
}

COMMANDS = {
    "/status": "Get current system health, last sweep time, source status",
    "/sweep": "Trigger a manual sweep cycle",
    "/brief": "Get a compact text summary of the latest intelligence",
    "/portfolio": "Show current positions and P&L (if Alpaca connected)",
    "/alerts": "Show recent alert history",
    "/mute": "Mute alerts for 1h (or /mute 2h, /mute 4h)",
    "/unmute": "Resume alerts",
    "/help": "Show available commands",
}


class TelegramAlerter:
    def __init__(self):
        self.bot_token = TELEGRAM_BOT_TOKEN
        self.chat_id = TELEGRAM_CHAT_ID
        self._configured = bool(self.bot_token and self.chat_id)
        self._alert_history: List[Dict] = []
        self._content_hashes: Dict[str, str] = {}
        self._mute_until: Optional[int] = None
        self._last_update_id = 0
        self._command_handlers: Dict[str, Callable] = {}
        self._polling_task: Optional[asyncio.Task] = None
        self._engine = None

    @property
    def is_configured(self) -> bool:
        return self._configured

    def set_engine(self, engine):
        self._engine = engine

    async def send_message(self, text: str, parse_mode: str = "Markdown") -> Dict:
        if not self._configured:
            return {"ok": False}
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    url,
                    json={
                        "chat_id": self.chat_id,
                        "text": text,
                        "parse_mode": parse_mode,
                    },
                )
                return response.json()
        except Exception:
            return {"ok": False}

    def _chunk_text(self, text: str, max_len: int = 4096) -> List[str]:
        if not text or len(text) <= max_len:
            return [text] if text else []
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + max_len, len(text))
            if end < len(text):
                last_newline = text.rfind("\n", start, end)
                if last_newline > start:
                    end = last_newline + 1
            chunks.append(text[start:end])
            start = end
        return chunks

    async def send_alert(self, message: str) -> bool:
        chunks = self._chunk_text(message)
        for chunk in chunks:
            result = await self.send_message(chunk)
            if not result.get("ok"):
                return False
        return True

    def _content_hash(self, signal: Dict) -> str:
        content = ""
        if signal.get("text"):
            text = signal["text"]
            content = (
                text.lower()
                .replace(r"\d{1,2}:\d{2}", "")
                .replace(r"\d+\.?\d*%?", "NUM")
                .replace(r"\s+", " ")
                .strip()[:120]
            )
        elif signal.get("label"):
            content = f"{signal['label']}:{signal.get('direction', 'none')}"
        else:
            content = signal.get("key", "")[:80]
        return hashlib.sha256(content.encode()).hexdigest()[:16]

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

    def _record_content_hash(self, signal: Dict):
        h = self._content_hash(signal)
        from datetime import datetime
        self._content_hashes[h] = datetime.now().isoformat()
        cutoff = datetime.now().timestamp() - 24 * 3600
        self._content_hashes = {
            k: v for k, v in self._content_hashes.items()
            if datetime.fromisoformat(v).timestamp() > cutoff
        }

    def _check_rate_limit(self, tier: str) -> bool:
        config = TIER_CONFIG.get(tier)
        if not config:
            return True
        now = asyncio.get_event_loop().time() if asyncio.get_event_loop().is_running() else 0
        last_same = None
        for a in reversed(self._alert_history):
            if a.get("tier") == tier:
                last_same = a
                break
        if last_same and (now * 1000 - last_same.get("timestamp", 0)) < config["cooldown_ms"]:
            return False
        one_hour_ago = now * 1000 - 3600 * 1000
        recent = sum(1 for a in self._alert_history if a.get("tier") == tier and a.get("timestamp", 0) > one_hour_go * 1000)
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

    def on_command(self, command: str, handler: Callable):
        self._command_handlers[command.lower()] = handler

    async def start_polling(self, interval_ms: int = 5000):
        if not self._configured or self._polling_task:
            return
        self._polling_task = asyncio.create_task(self._polling_loop(interval_ms))

    async def _polling_loop(self, interval_ms: int):
        while self._configured:
            try:
                await self._poll_updates()
            except Exception:
                pass
            await asyncio.sleep(interval_ms / 1000)

    async def _poll_updates(self):
        url = f"https://api.telegram.org/bot{self.bot_token}/getUpdates"
        params = {
            "offset": self._last_update_id + 1,
            "timeout": 0,
            "limit": 10,
            "allowed_updates": json.dumps(["message"]),
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params=params)
                data = response.json()
                if not data.get("ok") or not data.get("result"):
                    return
                for update in data["result"]:
                    self._last_update_id = max(self._last_update_id, update.get("update_id", 0))
                    msg = update.get("message", {})
                    if not msg.get("text"):
                        continue
                    chat_id = str(msg.get("chat", {}).get("id"))
                    if chat_id != str(self.chat_id):
                        continue
                    await self._handle_message(msg)
        except Exception:
            pass

    async def _handle_message(self, msg: Dict):
        text = msg.get("text", "").strip()
        parts = text.split()
        raw_command = parts[0].lower() if parts else ""
        command = self._normalize_command(raw_command)
        if not command:
            return
        args = " ".join(parts[1:])
        reply_chat_id = msg.get("chat", {}).get("id")
        message_id = msg.get("message_id")

        if command == "/help":
            help_text = "\n".join(f"{cmd} — {desc}" for cmd, desc in COMMANDS.items())
            await self.send_message(f"🤖 *CRUCIX BOT COMMANDS*\n\n{help_text}\n\n_Tip: Commands are case-insensitive_")
            return

        if command == "/mute":
            hours = float(args) if args else 1
            from time import time
            self._mute_until = time() * 1000 + hours * 3600 * 1000
            await self.send_message(f"🔇 Alerts muted for {hours}h")
            return

        if command == "/unmute":
            self._mute_until = None
            await self.send_message("🔔 Alerts resumed.")
            return

        if command == "/alerts":
            recent = self._alert_history[-10:]
            if not recent:
                await self.send_message("No recent alerts.")
                return
            lines = [f"{TIER_CONFIG.get(a['tier'], {}).get('emoji', '⚪')} {a['tier']}" for a in recent]
            await self.send_message(f"📋 *Recent Alerts ({len(recent)})*\n\n" + "\n".join(lines))
            return

        handler = self._command_handlers.get(command)
        if handler:
            try:
                response = await handler(args, message_id)
                if response:
                    await self.send_message(response)
            except Exception as e:
                await self.send_message(f"❌ Command failed: {e}")

    def _normalize_command(self, raw: str) -> Optional[str]:
        if not raw.startswith("/"):
            return None
        at_idx = raw.find("@")
        return raw if at_idx == -1 else raw[:at_idx]

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

        message = self._format_alert(evaluation, delta, tier)
        sent = await self.send_alert(message)

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
                "reason": "Safecast radiation monitors have flagged an anomaly. This requires immediate attention.",
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

    def _format_alert(self, evaluation: Dict, delta: Dict, tier: str) -> str:
        tc = TIER_CONFIG.get(tier, {})
        confidence_emoji = {"HIGH": "🟢", "MEDIUM": "🟡", "LOW": "⚪"}.get(evaluation.get("confidence", "MEDIUM"), "⚪")

        lines = [
            f"{tc.get('emoji', '⚪')} *CRUCIX {tc.get('label', 'ROUTINE')}*",
            "",
            f"*{evaluation.get('headline', 'Alert')}*",
            "",
            evaluation.get("reason", ""),
            "",
            f"Confidence: {confidence_emoji} {evaluation.get('confidence', 'MEDIUM')}",
            f"Direction: {delta.get('summary', {}).get('direction', 'mixed').upper()}",
        ]

        if evaluation.get("actionable") and evaluation["actionable"] != "Monitor":
            lines.extend(["", f"💡 *Action:* {evaluation['actionable']}"])

        if evaluation.get("signals"):
            lines.extend(["", "*Signals:*"])
            for sig in evaluation["signals"]:
                lines.append(f"• {sig}")

        from datetime import datetime
        lines.extend(["", f"_{datetime.utcnow().isoformat().replace('T', ' ')[:19]} UTC_"])

        return "\n".join(lines)