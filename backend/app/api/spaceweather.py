"""/api/spaceweather endpoints (NOAA SWPC, cached polling)."""
from fastapi import APIRouter

from ..services import noaa

router = APIRouter(prefix="/api/spaceweather", tags=["spaceweather"])


@router.get("")
async def get_spaceweather() -> dict:
    return await noaa.get_spaceweather()


@router.post("/refresh")
async def refresh_spaceweather() -> dict:
    return await noaa.get_spaceweather(force=True)
