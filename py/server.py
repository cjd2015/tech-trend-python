"""Crucix API Server - FastAPI-based intelligence dashboard"""
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
import uvicorn

from engine import CrucixEngine
from config import PORT


engine: CrucixEngine | None = None
start_time = datetime.utcnow()
sse_clients: set[asyncio.Queue] = set()


async def sse_generator(queue: asyncio.Queue):
    """Generate SSE events for a client."""
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
    """Application lifespan handler."""
    global engine
    
    engine = CrucixEngine(Path("runs"))
    
    try:
        existing = engine.load_latest()
        if existing:
            engine.current_data = existing
            print("[Crucix] Loaded existing data from runs/latest.json")
    except Exception:
        pass
    
    asyncio.create_task(run_periodic_sweep())
    
    print(f"[Crucix] Server ready on http://localhost:{PORT}")
    
    yield
    
    print("[Crucix] Shutting down...")


async def run_periodic_sweep():
    """Run periodic sweeps and broadcast to SSE clients."""
    from config import REFRESH_INTERVAL_MINUTES
    
    while True:
        try:
            if engine and not engine.sweep_in_progress:
                await engine.sweep()
                
                data = engine.get_dashboard_data()
                message = f'{{"type":"update","data":{str(data).replace("'", "\"")}}}'
                
                for queue in list(sse_clients):
                    try:
                        await queue.put(message)
                    except Exception:
                        sse_clients.discard(queue)
            
        except Exception as e:
            print(f"[Crucix] Sweep error: {e}")
        
        await asyncio.sleep(REFRESH_INTERVAL_MINUTES * 60)


app = FastAPI(
    title="Crucix Lite API",
    description="Lightweight OSINT Intelligence Engine",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the dashboard."""
    html_path = Path(__file__).parent / "dashboard" / "index.html"
    
    if html_path.exists():
        return HTMLResponse(content=html_path.read_text(encoding="utf-8"), status_code=200)
    
    return """
    <html><head><title>Crucix Lite</title></head>
    <body>
        <h1>Crucix Lite</h1>
        <p>Intelligence Engine Running</p>
        <ul>
            <li><a href="/api/data">API Data</a></li>
            <li><a href="/api/health">Health Check</a></li>
        </ul>
    </body></html>
    """


@app.get("/api/data")
async def get_data():
    """Get current intelligence data."""
    if not engine:
        return {"error": "Engine not initialized"}
    
    if not engine.current_data:
        return {"error": "No data yet - first sweep in progress"}
    
    return engine.get_dashboard_data()


@app.get("/api/health")
async def health_check():
    """Get system health status."""
    if not engine:
        return {"status": "initializing"}
    
    refresh_interval = 15
    next_sweep = None
    
    if engine.last_sweep_time:
        try:
            last = datetime.fromisoformat(engine.last_sweep_time.replace("Z", "+00:00"))
            next_sweep = (last + timedelta(minutes=refresh_interval)).isoformat()
        except Exception:
            pass
    
    return {
        "status": "ok",
        "uptime_seconds": (datetime.utcnow() - start_time).total_seconds(),
        "last_sweep": engine.last_sweep_time,
        "next_sweep": next_sweep,
        "sweep_in_progress": engine.sweep_in_progress,
        "sources_ok": engine.current_data.get("crucix", {}).get("sources_ok", 0) if engine.current_data else 0,
        "sources_failed": engine.current_data.get("crucix", {}).get("sources_failed", 0) if engine.current_data else 0,
    }


@app.post("/api/sweep")
async def trigger_sweep():
    """Manually trigger a sweep."""
    if not engine:
        return {"error": "Engine not initialized"}
    
    if engine.sweep_in_progress:
        return {"status": "already_in_progress"}
    
    asyncio.create_task(engine.sweep())
    return {"status": "sweep_triggered"}


@app.get("/api/events")
async def sse_events():
    """SSE stream for real-time updates."""
    queue = asyncio.Queue()
    sse_clients.add(queue)
    
    try:
        return StreamingResponse(
            sse_generator(queue),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
            },
        )
    finally:
        sse_clients.discard(queue)


@app.get("/api/delta")
async def get_delta():
    """Get delta from last sweep."""
    if not engine:
        return {"error": "Engine not initialized"}
    
    if not engine.last_delta:
        return {"error": "No delta available yet"}
    
    return {
        "timestamp": engine.last_delta.timestamp,
        "total_changes": engine.last_delta.total_changes,
        "critical_changes": engine.last_delta.critical_changes,
        "direction": engine.last_delta.direction,
        "signals": engine.last_delta.signals,
    }


def run():
    """Run the server."""
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=PORT,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    run()
