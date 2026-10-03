"""
Thesa AI — Python API Backend
Entry point FastAPI application.

Provides:
  - Generation jobs & SSE events (NeoMakalah engine)
  - Validation endpoints
  - Authentication (register, login, me)
  - Payment (Midtrans Snap, QRIS, simulate, webhook)
  - Supervisor AI & Viva Voce simulation
  - Administrative controlling & telemetry
  - Static frontend serving (/app, /workspace, /auth, /admin, /)
"""

import sys
import os
import time

# Tambahkan root Backend ke path agar bisa import engine NeoMakalah
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from python_api.config import settings
from python_api.routes import generations, validate, health, auth, payment, supervisor, admin
from python_api.services.db import init_db

SERVER_START_TIME = time.time()


# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown)
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inisialisasi resource saat startup, cleanup saat shutdown."""
    init_db()
    yield


# ---------------------------------------------------------------------------
# Aplikasi utama
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Thesa AI — Production Core API",
    description=(
        "Unified Python FastAPI backend untuk platform Thesa AI. "
        "Mengelola generation dokumen akademik, autentikasi, pembayaran, "
        "dan pendampingan akademik berbasis AI."
    ),
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers API
# ---------------------------------------------------------------------------

app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(payment.router, prefix="/api/v1/payment", tags=["payment"])
app.include_router(supervisor.router, prefix="/api/v1/supervisor", tags=["supervisor"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])
app.include_router(generations.router, prefix="/api/v1/generations", tags=["generations"])
app.include_router(validate.router, prefix="/api/v1/validate", tags=["validate"])


# ---------------------------------------------------------------------------
# Diagnostic & Legacy Health Parity
# ---------------------------------------------------------------------------

@app.get("/health", tags=["health"])
async def root_health():
    return {
        "status": "ok",
        "app": "Thesa AI / Python Production Core",
        "version": "1.0.0",
        "uptime_seconds": int(time.time() - SERVER_START_TIME),
        "database_connected": True,
        "primary_llm": os.environ.get("AI_PRIMARY_PROVIDER", "gemini"),
        "deepseek_configured": bool(os.environ.get("DEEPSEEK_API_KEY")),
        "gemini_configured": bool(os.environ.get("GEMINI_API_KEY")),
        "payment_configured": bool(os.environ.get("MIDTRANS_SERVER_KEY")),
    }


# ---------------------------------------------------------------------------
# Static Web Frontend & Clean URL Routing
# ---------------------------------------------------------------------------

# Cari direktori Frontend/web
workspace_root = os.path.dirname(backend_dir)
web_dir = os.path.join(workspace_root, "Frontend", "web")

if os.path.exists(web_dir):
    @app.get("/app", include_in_schema=False)
    async def serve_app():
        return FileResponse(os.path.join(web_dir, "app.html"))

    @app.get("/workspace", include_in_schema=False)
    async def serve_workspace():
        return FileResponse(os.path.join(web_dir, "app.html"))

    @app.get("/auth", include_in_schema=False)
    async def serve_auth():
        return FileResponse(os.path.join(web_dir, "auth.html"))

    @app.get("/admin", include_in_schema=False)
    async def serve_admin():
        return FileResponse(os.path.join(web_dir, "admin.html"))

    @app.get("/", include_in_schema=False)
    async def serve_root():
        landing_path = os.path.join(web_dir, "landing.html")
        if os.path.exists(landing_path):
            return FileResponse(landing_path)
        return FileResponse(os.path.join(web_dir, "index.html"))

    # Mount static files for assets (CSS, JS, images)
    app.mount("/", StaticFiles(directory=web_dir, html=True), name="static_web")
