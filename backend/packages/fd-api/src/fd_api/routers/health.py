"""Health route for load balancers and uptime checks."""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """The API is up."""

    ok: bool


@router.get("/health", operation_id="getHealth", summary="Check the API is up")
async def get_health() -> HealthResponse:
    """Answers without auth while the process serves requests."""
    return HealthResponse(ok=True)
