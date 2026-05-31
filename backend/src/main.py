"""Y.Scape FastAPI — Phase 1 entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes.native_tools import router as native_tools_router
from src.api.routes.settings import router as settings_router
from src.api.routes.tasks import demo_router, router as tasks_router
from src.api.routes.tools import router as tools_router
from src.api.run_manager import run_manager
from src.config import settings


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await run_manager.start_watchdog()
    yield
    await run_manager.stop_watchdog()


app = FastAPI(
    title="Y.Scape",
    description="Transactional Agent Runtime — Phase 7",
    version="0.7.0-phase7",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tasks_router)
app.include_router(demo_router)
app.include_router(tools_router)
app.include_router(native_tools_router)
app.include_router(settings_router)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "y-scape",
        "phase": 7,
        "demo_mode": settings.demo_mode,
        "model_provider": settings.model_provider,
        "model_name": settings.model_name,
        "api_key_configured": settings.api_key_configured,
    }
