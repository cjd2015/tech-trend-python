"""Crucix Engine - Main orchestrator"""
from __future__ import annotations
import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .sources import (
    SourceResult,
    gdelt, opensky, firms, ships, safecast, acled,
    reliefweb, who, ofac, opensanctions, adsb,
    treasury, gscpi, usaspending, comtrade,
    noaa, epa, patents, bluesky, reddit, telegram, kiwisdr,
    space, yfinance, cisa_kev, cloudflare_radar,
    tech,
    SOURCE_TIMEOUT,
)
from .delta import compute_delta
from .llm import create_llm_provider
from .llm.ideas import generate_trade_ideas
from .alerts.telegram import TelegramAlerter
from .alerts.discord import DiscordAlerter


class CrucixEngine:
    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or Path("runs")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.current_data: Optional[dict] = None
        self.previous_data: Optional[dict] = None
        self.last_delta: Optional[dict] = None
        self.last_sweep_time: Optional[str] = None
        self.sweep_in_progress = False
        
        self.llm_provider = create_llm_provider()
        self.telegram = TelegramAlerter()
        self.discord = DiscordAlerter()
        
        if self.llm_provider and self.llm_provider.is_configured:
            print(f"[Crucix] LLM enabled: {self.llm_provider.name}")
        
        if self.telegram.is_configured:
            print("[Crucix] Telegram alerts enabled")
        
        if self.discord.is_configured:
            print("[Crucix] Discord alerts enabled")
    
    async def run_source(self, name: str, fetch_fn) -> SourceResult:
        start = time.time()
        try:
            result = await asyncio.wait_for(fetch_fn(), timeout=SOURCE_TIMEOUT)
            return result
        except asyncio.TimeoutError:
            return SourceResult(name=name, status="error", duration_ms=(time.time()-start)*1000, error="Timeout")
        except Exception as e:
            return SourceResult(name=name, status="error", duration_ms=(time.time()-start)*1000, error=str(e))
    
    async def sweep(self) -> dict:
        if self.sweep_in_progress:
            return self.current_data or {}
        
        self.sweep_in_progress = True
        start_time = time.time()
        
        try:
            sources = [
                ("OpenSky", opensky.briefing),
                ("FIRMS", firms.briefing),
                ("Maritime", ships.briefing),
                ("Safecast", safecast.briefing),
                ("ACLED", acled.briefing),
                ("ReliefWeb", reliefweb.briefing),
                ("WHO", who.briefing),
                ("OFAC", ofac.briefing),
                ("OpenSanctions", opensanctions.briefing),
                ("ADS-B", adsb.briefing),
                ("Treasury", treasury.briefing),
                ("GSCPI", gscpi.briefing),
                ("USAspending", usaspending.briefing),
                ("Comtrade", comtrade.briefing),
                ("NOAA", noaa.briefing),
                ("EPA", epa.briefing),
                ("Patents", patents.briefing),
                ("Bluesky", bluesky.briefing),
                ("Reddit", reddit.briefing),
                ("Telegram", telegram.briefing),
                ("KiwiSDR", kiwisdr.briefing),
                ("Space", space.briefing),
                ("YFinance", yfinance.briefing),
                ("CISA-KEV", cisa_kev.briefing),
                ("Cloudflare-Radar", cloudflare_radar.briefing),
                ("HackerNews", tech.hackernews_top),
                ("GitHub", tech.github_trending),
                ("AI-Projects", tech.ai_news),
                ("Autonomous", tech.autonomous_news),
            ]
            
            tasks = [self.run_source(name, fn) for name, fn in sources]
            results = await asyncio.gather(*tasks)
            
            source_data = {}
            errors = []
            timing = {}
            sources_ok = 0
            
            for result in results:
                if result.ok:
                    sources_ok += 1
                    source_data[result.name] = result.data
                else:
                    errors.append({"name": result.name, "error": result.error})
                
                timing[result.name] = {"status": result.status, "ms": round(result.duration_ms, 1)}
            
            self.previous_data = self.current_data
            
            output = {
                "crucix": {
                    "version": "2.0.0",
                    "timestamp": datetime.utcnow().isoformat(),
                    "duration_ms": round((time.time() - start_time) * 1000, 1),
                    "sources_queried": len(sources),
                    "sources_ok": sources_ok,
                    "sources_failed": len(sources) - sources_ok,
                },
                "sources": source_data,
                "errors": errors,
                "timing": timing,
            }
            
            self.current_data = output
            self.last_sweep_time = output["crucix"]["timestamp"]
            
            synthesized = self._synthesize(output)
            if self.previous_data:
                prev_synth = self._synthesize(self.previous_data)
                self.last_delta = compute_delta(synthesized, prev_synth)
            
            if self.llm_provider and self.llm_provider.is_configured:
                try:
                    ideas = await generate_trade_ideas(self.llm_provider, synthesized, self.last_delta)
                    synthesized["ideas"] = ideas
                    synthesized["ideas_source"] = "llm"
                except Exception as e:
                    print(f"[Crucix] LLM ideas failed: {e}")
            
            if self.last_delta and self.last_delta.get("summary", {}).get("totalChanges", 0) > 0:
                await self.telegram.evaluate_and_alert(self.llm_provider, self.last_delta, None)
                await self.discord.evaluate_and_alert(self.llm_provider, self.last_delta, None)
            
            output["synthesized"] = synthesized
            
            self._save_latest(output)
            
            print(f"[Crucix] Sweep complete: {sources_ok}/{len(sources)} sources OK")
            
            return output
            
        finally:
            self.sweep_in_progress = False
    
    def _synthesize(self, data: dict) -> dict:
        sources = data.get("sources", {})
        return {
            "timestamp": data.get("crucix", {}).get("timestamp"),
            "meta": data.get("crucix"),
            "markets": sources.get("YFinance", {}),
            "space": sources.get("Space", {}),
            "opensky": sources.get("OpenSky", {}),
            "telegram": sources.get("Telegram", {}),
            "acled": sources.get("ACLED", {}),
            "news": sources.get("GDELT", {}),
            "hackernews": sources.get("HackerNews", {}),
            "github": sources.get("GitHub", {}),
            "ai_projects": sources.get("AI-Projects", {}),
            "autonomous": sources.get("Autonomous", {}),
            "signals": self._collect_signals(sources),
        }
    
    def _collect_signals(self, sources: dict) -> list:
        signals = []
        for name, source in sources.items():
            if isinstance(source, dict) and source.get("signals"):
                signals.extend(source["signals"])
        return signals[:20]
    
    def _save_latest(self, data: dict):
        latest_path = self.data_dir / "latest.json"
        with open(latest_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def load_latest(self) -> Optional[dict]:
        latest_path = self.data_dir / "latest.json"
        if latest_path.exists():
            with open(latest_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None
    
    def get_dashboard_data(self) -> dict:
        if not self.current_data:
            return {}
        
        synthesized = self.current_data.get("synthesized", self._synthesize(self.current_data))
        
        return {
            "meta": self.current_data.get("crucix"),
            "markets": synthesized.get("markets", {}),
            "space": synthesized.get("space", {}),
            "opensky": synthesized.get("opensky", {}),
            "telegram": synthesized.get("telegram", {}),
            "acled": synthesized.get("acled", {}),
            "news": synthesized.get("news", {}),
            "hackernews": synthesized.get("hackernews", {}),
            "github": synthesized.get("github", {}),
            "ai_projects": synthesized.get("ai_projects", {}),
            "autonomous": synthesized.get("autonomous", {}),
            "signals": synthesized.get("signals", []),
            "ideas": synthesized.get("ideas", []),
            "delta": self.last_delta,
            "health": self._get_health(),
        }
    
    def _get_health(self) -> list:
        if not self.current_data:
            return []
        
        health = []
        timing = self.current_data.get("timing", {})
        errors = {e["name"]: e["error"] for e in self.current_data.get("errors", [])}
        
        for name, info in timing.items():
            health.append({
                "name": name,
                "ok": info.get("status") == "ok",
                "error": errors.get(name),
            })
        
        return health
