from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from typing import Optional, Literal, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.registration import Registration
from app.services.meta_capi_service import meta_capi_service
from app.core.logging import logger

router = APIRouter()


class TrackMetaEventRequest(BaseModel):
    event_name: Literal["PageView", "ViewContent", "Lead", "InitiateCheckout", "Purchase", "CompleteRegistration"]
    event_id: Optional[str] = None
    session_id: Optional[str] = "anon_session"
    registration_code: Optional[str] = None
    category_code: Optional[str] = None
    category_title: Optional[str] = None
    price_inr: Optional[float] = None
    event_source_url: Optional[str] = None
    fbc: Optional[str] = None
    fbp: Optional[str] = None


@router.post(
    "/events",
    summary="Ingest server-side Meta Conversions API events from frontend or backend triggers",
)
async def track_meta_event(
    payload: TrackMetaEventRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Ingest conversion events and dispatch them server-side to Meta CAPI.
    Captures client IP and User Agent headers for accurate attribution matching.
    """
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    reg_id = None
    if payload.registration_code:
        q = select(Registration).where(Registration.registration_code == payload.registration_code)
        res = await db.execute(q)
        reg = res.scalar_one_or_none()
        if reg:
            reg_id = reg.id

    res: Dict[str, Any] = {}
    if payload.event_name == "PageView":
        res = await meta_capi_service.track_page_view(
            db=db,
            session_id=payload.session_id or "session_default",
            url=payload.event_source_url,
            client_ip=client_ip,
            user_agent=user_agent,
            fbc=payload.fbc,
            fbp=payload.fbp,
        )
    elif payload.event_name == "ViewContent":
        res = await meta_capi_service.track_view_content(
            db=db,
            category_code=payload.category_code or "21K",
            category_title=payload.category_title or "Half Marathon 21K",
            price_inr=payload.price_inr or 899.0,
            session_id=payload.session_id or "session_default",
            client_ip=client_ip,
            user_agent=user_agent,
            fbc=payload.fbc,
            fbp=payload.fbp,
        )
    elif payload.event_name == "Lead":
        if not reg_id:
            raise HTTPException(status_code=400, detail="registration_code required for Lead event")
        res = await meta_capi_service.track_lead(
            db=db, registration_id=reg_id, client_ip=client_ip, user_agent=user_agent, fbc=payload.fbc, fbp=payload.fbp
        )
    elif payload.event_name == "InitiateCheckout":
        if not reg_id:
            raise HTTPException(status_code=400, detail="registration_code required for InitiateCheckout event")
        res = await meta_capi_service.track_initiate_checkout(
            db=db, registration_id=reg_id, client_ip=client_ip, user_agent=user_agent, fbc=payload.fbc, fbp=payload.fbp
        )
    elif payload.event_name == "Purchase":
        if not reg_id:
            raise HTTPException(status_code=400, detail="registration_code required for Purchase event")
        res = await meta_capi_service.track_purchase(
            db=db, registration_id=reg_id, client_ip=client_ip, user_agent=user_agent, fbc=payload.fbc, fbp=payload.fbp
        )
    elif payload.event_name == "CompleteRegistration":
        if not reg_id:
            raise HTTPException(status_code=400, detail="registration_code required for CompleteRegistration event")
        res = await meta_capi_service.track_complete_registration(
            db=db, registration_id=reg_id, client_ip=client_ip, user_agent=user_agent, fbc=payload.fbc, fbp=payload.fbp
        )

    return {"status": "success", "event_name": payload.event_name, "meta_result": res}


@router.post(
    "/simulate-event",
    summary="Developer endpoint to simulate and demonstrate Meta CAPI events on demand",
)
async def simulate_meta_event(
    payload: TrackMetaEventRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Developer demonstration endpoint to test and verify Meta CAPI tracking flows."""
    return await track_meta_event(payload=payload, request=request, db=db)
