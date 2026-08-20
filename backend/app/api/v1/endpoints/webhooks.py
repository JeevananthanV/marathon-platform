import json
from fastapi import APIRouter, Request, Header, Depends, HTTPException, Query, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any

from app.db.session import get_db
from app.services.payment_service import PaymentService
from app.services.whatsapp import whatsapp_service, delivery_handler
from app.core.config import settings
from app.core.logging import logger

router = APIRouter()


@router.post(
    "/razorpay",
    status_code=status.HTTP_200_OK,
    summary="Razorpay webhook listener with HMAC signature verification & idempotency",
)
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: Optional[str] = Header(None, alias="X-Razorpay-Signature"),
    db: AsyncSession = Depends(get_db),
):
    """
    Handle asynchronous Razorpay payment events (payment.captured, payment.failed, order.paid).
    Guarantees idempotency to prevent duplicate registration or bib assignment.
    """
    if not x_razorpay_signature:
        logger.warning("Received webhook without X-Razorpay-Signature header.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing X-Razorpay-Signature header.",
        )

    raw_body = await request.body()
    
    result = await PaymentService.process_webhook(
        db=db,
        raw_body=raw_body,
        signature=x_razorpay_signature,
    )
    return result


@router.get(
    "/whatsapp",
    summary="WhatsApp Cloud API Webhook Subscription Verification",
)
async def verify_whatsapp_webhook(
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge"),
):
    """
    Meta Graph API Webhook challenge verification endpoint.
    Meta validates endpoint by sending GET request with hub.mode, hub.verify_token, and hub.challenge.
    """
    if hub_mode == "subscribe" and hub_verify_token == settings.WHATSAPP_WEBHOOK_VERIFY_TOKEN:
        logger.info("[WHATSAPP WEBHOOK] Challenge verification successful.")
        return PlainTextResponse(content=hub_challenge or "")

    logger.warning("[WHATSAPP WEBHOOK] Challenge verification failed - invalid verify token.")
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Verification token mismatch.",
    )


@router.post(
    "/whatsapp",
    status_code=status.HTTP_200_OK,
    summary="WhatsApp Cloud API Inbound Webhook Listener (Delivery Receipts & Status Updates)",
)
async def receive_whatsapp_webhook(
    request: Request,
    x_hub_signature_256: Optional[str] = Header(None, alias="X-Hub-Signature-256"),
    db: AsyncSession = Depends(get_db),
):
    """
    Inbound WhatsApp status updates handler (sent -> delivered -> read -> failed).
    Validates HMAC signature and updates message status in database ledger.
    """
    raw_body = await request.body()

    # Validate signature if provided
    if x_hub_signature_256:
        is_valid = whatsapp_service.get_provider().validate_webhook_signature(
            raw_body=raw_body,
            signature_header=x_hub_signature_256,
        )
        if not is_valid:
            logger.warning("[WHATSAPP WEBHOOK] Rejected invalid X-Hub-Signature-256 signature.")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature.",
            )

    try:
        payload = json.loads(raw_body.decode("utf-8")) if raw_body else {}
    except Exception as e:
        logger.warning(f"Malformed JSON in WhatsApp webhook: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload.",
        )

    result = await delivery_handler.process_webhook_payload(db=db, payload=payload)
    return {"status": "ok", "data": result}
