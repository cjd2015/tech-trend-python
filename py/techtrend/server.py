"""TechTrend API Server"""
from __future__ import annotations
import asyncio
import json
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
import uvicorn

from .config import PORT, REFRESH_INTERVAL_MINUTES
from .engine import TechTrendEngine
from .i18n import get_locale, current_language, get_supported_locales


engine: TechTrendEngine | None = None
start_time = datetime.utcnow()
sse_clients: set[asyncio.Queue] = set()
loading_page_path = Path(__file__).parent.parent / "dashboard" / "public" / "loading.html"
dashboard_path = Path(__file__).parent / "dashboard" / "index.html"


async def sse_generator(queue: asyncio.Queue):
    try:
        yield "data: {\"type\":\"connected\"}\n\n"
        while True:
            try:
                data = await asyncio.wait_for(queue.get(), timeout=30)
                yield f"data: {data}\n\n"
            except asyncio.TimeoutError:
                yield "data: {\"type\":\"ping\"}\n\n"
    except GeneratorExit:
        pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    global engine
    
    engine = TechTrendEngine(Path("runs"))
    engine.telegram.set_engine(engine)
    
    try:
        existing = engine.load_latest()
        if existing:
            engine.current_data = existing
            print("[Crucix] Loaded existing data from runs/latest.json")
    except Exception:
        pass
    
    engine.telegram.on_command("/status", _handle_status_command)
    engine.telegram.on_command("/sweep", _handle_sweep_command)
    engine.telegram.on_command("/brief", _handle_brief_command)
    engine.telegram.on_command("/portfolio", _handle_portfolio_command)
    
    if engine.telegram.is_configured:
        await engine.telegram.start_polling()
    
    asyncio.create_task(run_periodic_sweep())
    print(f"[Crucix] Server ready on http://localhost:{PORT}")
    
    yield
    
    print("[Crucix] Shutting down...")


async def _handle_status_command(args: str, message_id: int) -> str:
    if not engine:
        return "Engine not initialized"
    
    uptime = int((datetime.utcnow() - start_time).total_seconds())
    h = uptime // 3600
    m = (uptime % 3600) // 60
    sources_ok = engine.current_data.get("crucix", {}).get("sources_ok", 0) if engine.current_data else 0
    sources_total = engine.current_data.get("crucix", {}).get("sources_queried", 0) if engine.current_data else 0
    sources_failed = engine.current_data.get("crucix", {}).get("sources_failed", 0) if engine.current_data else 0
    llm_status = f"✅ {engine.llm_provider.name}" if engine.llm_provider and engine.llm_provider.is_configured else "❌ Disabled"
    
    next_sweep = "pending"
    if engine.last_sweep_time:
        try:
            last = datetime.fromisoformat(engine.last_sweep_time)
            next_time = last + timedelta(minutes=REFRESH_INTERVAL_MINUTES)
            next_sweep = next_time.strftime("%H:%M:%S")
        except:
            pass
    
    return f"""🖥️ *CRUCIX STATUS*

Uptime: {h}h {m}m
Last sweep: {engine.last_sweep_time or 'never'}
Next sweep: {next_sweep} UTC
Sweep in progress: {'🔄 Yes' if engine.sweep_in_progress else '⏸️ No'}
Sources: {sources_ok}/{sources_total} OK{f' ({sources_failed} failed)' if sources_failed > 0 else ''}
LLM: {llm_status}
SSE clients: {len(sse_clients)}
Dashboard: http://localhost:{PORT}"""


async def _handle_sweep_command(args: str, message_id: int) -> str:
    if not engine:
        return "Engine not initialized"
    if engine.sweep_in_progress:
        return "🔄 Sweep already in progress"
    asyncio.create_task(engine.sweep())
    return "🚀 Manual sweep triggered"


async def _handle_brief_command(args: str, message_id: int) -> str:
    if not engine or not engine.current_data:
        return "⏳ No data yet"
    
    synthesized = engine.current_data.get("synthesized", {})
    delta = engine.last_delta
    ideas = synthesized.get("ideas", [])[:3]
    
    sections = [f"📋 *CRUCIX BRIEF*\n_{datetime.utcnow().isoformat().replace('T', ' ')[:19]} UTC_\n"]
    
    if delta and delta.get("summary"):
        d = delta["summary"]
        direction_emoji = {"risk-off": "📉", "risk-on": "📈", "mixed": "↔️"}.get(d.get("direction", "mixed"), "↔️")
        sections.append(f"{direction_emoji} Direction: *{d.get('direction', 'mixed').upper()}* | {d.get('totalChanges', 0)} changes, {d.get('criticalChanges', 0)} critical\n")
    
    markets = synthesized.get("markets", {})
    energy = synthesized.get("energy", {})
    
    if markets or energy:
        vix = markets.get("vix")
        gold = markets.get("gold")
        wti = energy.get("wti")
        sections.append(f"📊 VIX: {vix or '--'} | WTI: ${wti or '--'} | Gold: ${gold or '--'}\n")
    
    tg = synthesized.get("telegram", {})
    if tg and tg.get("urgent"):
        sections.append(f"📡 OSINT: {len(tg['urgent'])} urgent signals\n")
    
    if ideas:
        sections.append("💡 *Top Ideas:*")
        for idea in ideas:
            emoji = {"long": "📈", "hedge": "🛡️", "neutral": "👁️"}.get(idea.get("type", "long"), "📈")
            sections.append(f"  {emoji} {idea.get('title', '')}")
    
    return "\n".join(sections)


async def _handle_portfolio_command(args: str, message_id: int) -> str:
    return "📊 Portfolio integration requires Alpaca MCP connection."


async def run_periodic_sweep():
    while True:
        try:
            if engine and not engine.sweep_in_progress:
                data = await engine.sweep()
                dashboard_data = engine.get_dashboard_data()
                message = json.dumps({"type": "update", "data": dashboard_data})
                for queue in list(sse_clients):
                    try:
                        await queue.put(message)
                    except Exception:
                        sse_clients.discard(queue)
        except Exception as e:
            print(f"[Crucix] Sweep error: {e}")
        
        await asyncio.sleep(REFRESH_INTERVAL_MINUTES * 60)


app = FastAPI(title="Crucix API", version="2.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_class=HTMLResponse)
async def root():
    if not engine or not engine.current_data:
        if loading_page_path.exists():
            return HTMLResponse(content=loading_page_path.read_text(encoding="utf-8"), status_code=200)
        return """<html><head><title>Crucix Loading</title></head><body><h1>Initializing Crucix...</h1></body></html>"""
    
    if dashboard_path.exists():
        html = dashboard_path.read_text(encoding="utf-8")
        locale = get_locale()
        locale_script = f'<script>window.__CRUCIX_LOCALE__ = {json.dumps(locale).replace("</script>", "<\\/script>")};</script>'
        html = html.replace("</head>", f"{locale_script}\n</head>")
        return HTMLResponse(content=html, status_code=200)
    
    return """<html><head><title>Crucix</title></head><body>
    <h1>Crucix Intelligence Engine</h1>
    <p>API: <a href="/api/data">/api/data</a> | <a href="/api/health">/api/health</a></p>
    </body></html>"""


@app.get("/api/data")
async def get_data():
    if not engine:
        return {"error": "Engine not initialized"}
    if not engine.current_data:
        return {"error": "No data yet"}
    return engine.get_dashboard_data()


@app.get("/api/health")
async def health():
    if not engine:
        return {"status": "initializing"}
    
    next_sweep = None
    if engine.last_sweep_time:
        try:
            last = datetime.fromisoformat(engine.last_sweep_time)
            next_sweep = (last + timedelta(minutes=REFRESH_INTERVAL_MINUTES)).isoformat()
        except Exception:
            pass
    
    return {
        "status": "ok",
        "uptime": int((datetime.utcnow() - start_time).total_seconds()),
        "uptime_seconds": int((datetime.utcnow() - start_time).total_seconds()),
        "last_sweep": engine.last_sweep_time,
        "next_sweep": next_sweep,
        "sweep_in_progress": engine.sweep_in_progress,
        "sources_ok": engine.current_data.get("crucix", {}).get("sources_ok", 0) if engine.current_data else 0,
        "sources_failed": engine.current_data.get("crucix", {}).get("sources_failed", 0) if engine.current_data else 0,
        "llm_enabled": bool(engine.llm_provider and engine.llm_provider.is_configured),
        "llm_provider": engine.llm_provider.name if engine.llm_provider else None,
        "telegram_enabled": engine.telegram.is_configured,
        "refresh_interval_minutes": REFRESH_INTERVAL_MINUTES,
        "language": current_language,
    }


@app.get("/api/locales")
async def locales():
    return {
        "current": current_language,
        "supported": get_supported_locales(),
    }


@app.post("/api/sweep")
async def trigger_sweep():
    if not engine:
        return {"error": "Engine not initialized"}
    if engine.sweep_in_progress:
        return {"status": "already_in_progress"}
    asyncio.create_task(engine.sweep())
    return {"status": "sweep_triggered"}


@app.get("/api/events")
async def sse_events():
    queue = asyncio.Queue()
    sse_clients.add(queue)
    try:
        return StreamingResponse(
            sse_generator(queue),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "Access-Control-Allow-Origin": "*"},
        )
    finally:
        sse_clients.discard(queue)


@app.get("/api/delta")
async def get_delta():
    if not engine:
        return {"error": "Engine not initialized"}
    if not engine.last_delta:
        return {"error": "No delta available"}
    return engine.last_delta


def run():
    uvicorn.run("crucix.server:app", host="0.0.0.0", port=PORT, reload=False, log_level="info")


if __name__ == "__main__":
    run()