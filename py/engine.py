"""Crucix Engine - Main orchestrator for intelligence gathering"""
import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from sources import (
    SourceResult,
    fetch_fred,
    fetch_yfinance,
    fetch_eia,
    fetch_firms,
    fetch_space,
    fetch_news,
    fetch_opensky,
)
from delta import compute_delta, DeltaResult
from config import REFRESH_INTERVAL_MINUTES


class CrucixEngine:
    """Main intelligence engine that orchestrates all data sources."""
    
    def __init__(self, data_dir: Path | None = None):
        self.data_dir = data_dir or Path("runs")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.current_data: dict[str, Any] | None = None
        self.previous_data: dict[str, Any] | None = None
        self.last_delta: DeltaResult | None = None
        self.last_sweep_time: str | None = None
        self.sweep_in_progress = False
    
    async def run_source(self, name: str, fetch_fn) -> SourceResult:
        """Run a single source with timeout."""
        start = time.time()
        try:
            result = await asyncio.wait_for(fetch_fn(), timeout=30.0)
            return result
        except asyncio.TimeoutError:
            return SourceResult(
                name=name,
                status="error",
                duration_ms=(time.time() - start) * 1000,
                error=f"Timeout after 30s",
            )
        except Exception as e:
            return SourceResult(
                name=name,
                status="error",
                duration_ms=(time.time() - start) * 1000,
                error=str(e),
            )
    
    async def sweep(self) -> dict[str, Any]:
        """Run all sources in parallel and return aggregated results."""
        if self.sweep_in_progress:
            return self.current_data or {}
        
        self.sweep_in_progress = True
        start_time = time.time()
        
        try:
            sources = [
                ("FRED", fetch_fred),
                ("YFinance", fetch_yfinance),
                ("EIA", fetch_eia),
                ("FIRMS", fetch_firms),
                ("Space", fetch_space),
                ("News", fetch_news),
                ("OpenSky", fetch_opensky),
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
                
                timing[result.name] = {
                    "status": result.status,
                    "ms": round(result.duration_ms, 1),
                }
            
            self.previous_data = self.current_data
            
            output = {
                "crucix": {
                    "version": "1.0.0",
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
            
            if self.previous_data:
                self.last_delta = compute_delta(
                    self._synthesize(output),
                    self._synthesize(self.previous_data)
                )
            
            self._save_latest(output)
            
            return output
            
        finally:
            self.sweep_in_progress = False
    
    def _synthesize(self, data: dict) -> dict:
        """Convert raw source data to dashboard format."""
        synthesized = {
            "timestamp": data.get("crucix", {}).get("timestamp"),
            "fred": data.get("sources", {}).get("FRED", {}),
            "markets": data.get("sources", {}).get("YFinance", {}),
            "eia": data.get("sources", {}).get("EIA", {}),
            "firms": data.get("sources", {}).get("FIRMS", {}),
            "space": data.get("sources", {}).get("Space", {}),
            "news": data.get("sources", {}).get("News", {}),
            "opensky": data.get("sources", {}).get("OpenSky", {}),
        }
        return synthesized
    
    def _save_latest(self, data: dict):
        """Save latest sweep to disk."""
        latest_path = self.data_dir / "latest.json"
        with open(latest_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def load_latest(self) -> dict | None:
        """Load the most recent sweep from disk."""
        latest_path = self.data_dir / "latest.json"
        if latest_path.exists():
            with open(latest_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None
    
    def get_dashboard_data(self) -> dict:
        """Get data formatted for dashboard consumption."""
        if not self.current_data:
            return {}
        
        synthesized = self._synthesize(self.current_data)
        
        return {
            "meta": self.current_data.get("crucix"),
            "health": self._get_health(),
            "fred": synthesized.get("fred", {}).get("indicators", []),
            "markets": synthesized.get("markets", {}),
            "energy": synthesized.get("eia", {}).get("oil_prices", {}),
            "firms": synthesized.get("firms", {}),
            "space": synthesized.get("space", {}),
            "news": synthesized.get("news", {}).get("articles", []),
            "opensky": synthesized.get("opensky", {}),
            "delta": self.last_delta,
        }
    
    def _get_health(self) -> list[dict]:
        """Get source health status."""
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
                "duration_ms": info.get("ms"),
            })
        
        return health
    
    async def start_periodic_sweep(self, callback=None):
        """Start periodic sweep cycle."""
        while True:
            await self.sweep()
            
            if callback:
                callback(self.get_dashboard_data())
            
            await asyncio.sleep(REFRESH_INTERVAL_MINUTES * 60)


if __name__ == "__main__":
    async def main():
        engine = CrucixEngine()
        
        print("Running intelligence sweep...")
        result = await engine.sweep()
        
        print(f"\nSweep complete in {result['crucix']['duration_ms']}ms")
        print(f"Sources OK: {result['crucix']['sources_ok']}/{result['crucix']['sources_queried']}")
        
        dashboard = engine.get_dashboard_data()
        print(f"\nDashboard data keys: {list(dashboard.keys())}")
        
        if engine.last_delta:
            print(f"\nDelta: {engine.last_delta.total_changes} changes, direction: {engine.last_delta.direction}")
    
    asyncio.run(main())
