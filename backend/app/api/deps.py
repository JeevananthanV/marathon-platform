import secrets
from fastapi import Header, Query, HTTPException, status
from typing import Optional
from app.core.config import settings


async def verify_admin_auth(
    x_admin_api_key: Optional[str] = Header(None, alias="X-Admin-API-Key"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    admin_key: Optional[str] = Query(None, alias="admin_key"),
) -> str:
    """
    Authenticate administrative requests.
    Accepts:
    1. Header: X-Admin-API-Key: <key>
    2. Header: Authorization: Bearer <key>
    3. Query Parameter: ?admin_key=<key> (useful for CSV export browser downloads)
    """
    provided_key = None

    if x_admin_api_key:
        provided_key = x_admin_api_key.strip()
    elif authorization:
        parts = authorization.strip().split()
        if len(parts) == 2 and parts[0].lower() in ["bearer", "token", "apikey"]:
            provided_key = parts[1]
        elif len(parts) == 1:
            provided_key = parts[0]
    elif admin_key:
        provided_key = admin_key.strip()

    if not provided_key or not secrets.compare_digest(provided_key, settings.ADMIN_API_KEY):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: Invalid or missing Admin API Key.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return "admin_authenticated"
