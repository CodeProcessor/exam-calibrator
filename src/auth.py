"""API key authentication for FastAPI endpoints."""

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader

from config import settings

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(api_key: str | None = Depends(API_KEY_HEADER)) -> None:
    """Verify the API key. If settings.api_key is unset, no auth is required."""
    if settings.api_key is None:
        return
    if api_key is None or api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key. Provide X-API-Key header.",
        )
