"""Health router.

Liveness probe. Unlike the feature endpoints, this MUST return a real 200 so
Docker health checks and the startup smoke test can rely on it.
"""

from __future__ import annotations

from fastapi import APIRouter

from app import __version__
from app.api.dependencies import SettingsDep
from app.api.v1.schemas.common import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health(settings: SettingsDep) -> HealthResponse:
    """Return service liveness."""
    return HealthResponse(
        status="ok",
        service=settings.app.name,
        version=__version__,
    )
