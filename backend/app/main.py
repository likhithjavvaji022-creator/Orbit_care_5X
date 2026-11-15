"""ORBITCARE 5X FastAPI application entry point.

Serves the JSON API under /api and the static frontend at / when the
frontend/ directory exists.
"""
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import db
from .api import assessments, reports, settings, spaceweather, telemetry

APP_VERSION = "0.1.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    yield


app = FastAPI(title="ORBITCARE 5X", version=APP_VERSION, lifespan=lifespan)

# "null" is the Origin sent by file:// pages. Local-only default; no wildcard.
DEFAULT_CORS_ORIGINS = "null,http://localhost:8090,http://127.0.0.1:8090"
CORS_ORIGINS = [
    o.strip()
    for o in os.environ.get("CORS_ORIGINS", DEFAULT_CORS_ORIGINS).split(",")
    if o.strip() and o.strip() != "*"
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
    allow_credentials=False,
)
app.include_router(telemetry.router)
app.include_router(assessments.router)
app.include_router(spaceweather.router)
app.include_router(settings.router)
app.include_router(reports.router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "version": APP_VERSION}


# parents[0]=app, parents[1]=backend, parents[2]=project root
FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
if FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")



