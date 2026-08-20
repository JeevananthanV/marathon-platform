from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field
from typing import Optional, Literal, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.registration import Registration
from app.integrations.n8n import n8n_client
from app.services.n8n_service import n8n_service
from app.services.whatsapp_service import whatsapp_service
from app.services.zoho_service import zoho_service
from app.core.logging import logger

router = APIRouter()


class TriggerActionRequest(BaseModel):
    action: Literal["whatsapp_reminder", "whatsapp_pass", "whatsapp_confirmation", "zoho_sync"]
    registration_id: str
    reminder_type: Optional[Literal["7_days", "1_day", "event_day"]] = None


class SimulateEventRequest(BaseModel):
    event: Literal["registration.confirmed", "payment.captured", "bib.assigned", "reminder.7_days", "reminder.1_day", "reminder.event_day"]
    registration_code: str


def verify_n8n_auth(x_n8n_webhook_secret: Optional[str] = Header(None, alias="X-N8N-Webhook-Secret")) -> None:
    """Dependency to enforce webhook shared-secret authentication for n8n incoming requests."""
    if not x_n8n_webhook_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-N8N-Webhook-Secret authentication header.",
        )
    if not n8n_client.verify_webhook_secret(x_n8n_webhook_secret):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid X-N8N-Webhook-Secret token.",
        )


@router.get(
    "/eligible-participants",
    summary="Fetch CONFIRMED participants eligible for n8n scheduled reminders",
    dependencies=[Depends(verify_n8n_auth)],
)
async def get_eligible_participants(
    reminder_type: str = Query("7_days", description="Reminder stage: 7_days, 1_day, event_day"),
    db: AsyncSession = Depends(get_db),
):
    """
    Endpoint called by n8n scheduled reminder workflows to retrieve verified participants.
    Strictly filters for CONFIRMED registrations only.
    """
    participants = await n8n_service.get_eligible_reminder_participants(db=db, reminder_type=reminder_type)
    return {
        "status": "success",
        "reminder_type": reminder_type,
        "count": len(participants),
        "participants": participants,
    }


@router.post(
    "/trigger-action",
    summary="n8n callback to trigger backend WhatsApp or Zoho action without duplicating logic",
    dependencies=[Depends(verify_n8n_auth)],
)
async def trigger_automation_action(
    payload: TriggerActionRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Orchestration endpoint enabling n8n workflows to invoke backend services securely.
    Ensures WhatsApp and Zoho business logic remains centralized in the FastAPI backend.
    """
    reg_id = payload.registration_id

    if payload.action == "whatsapp_confirmation":
        res = await whatsapp_service.send_registration_confirmation(db=db, registration_id=reg_id)
    elif payload.action == "whatsapp_pass":
        res = await whatsapp_service.send_digital_pass(db=db, registration_id=reg_id)
    elif payload.action == "whatsapp_reminder":
        if not payload.reminder_type:
            raise HTTPException(status_code=400, detail="Missing reminder_type for whatsapp_reminder action.")
        if payload.reminder_type == "7_days":
            res = await whatsapp_service.send_reminder_7_days(db=db, registration_id=reg_id)
        elif payload.reminder_type == "1_day":
            res = await whatsapp_service.send_reminder_1_day(db=db, registration_id=reg_id)
        elif payload.reminder_type == "event_day":
            res = await whatsapp_service.send_reminder_event_day(db=db, registration_id=reg_id)
    elif payload.action == "zoho_sync":
        res = await zoho_service.sync_registration_to_zoho(db=db, registration_id=reg_id)
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported action: {payload.action}")

    return {"status": "success", "action": payload.action, "result": res}


@router.post(
    "/simulate-event",
    summary="Developer endpoint to trigger and demonstrate n8n automation events on demand",
)
async def simulate_n8n_event(
    payload: SimulateEventRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Developer demonstration endpoint to test n8n event dispatches and full workflow traces.
    """
    query = select(Registration).where(Registration.registration_code == payload.registration_code)
    result = await db.execute(query)
    reg = result.scalar_one_or_none()

    if not reg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Registration '{payload.registration_code}' not found.",
        )

    res = {}
    if payload.event == "registration.confirmed":
        res = await n8n_service.dispatch_registration_confirmed(db=db, registration_id=reg.id)
    elif payload.event == "payment.captured":
        res = await n8n_service.dispatch_payment_captured(db=db, registration_id=reg.id)
    elif payload.event == "bib.assigned":
        res = await n8n_service.dispatch_bib_assigned(db=db, registration_id=reg.id)
    elif payload.event.startswith("reminder."):
        rem_type = payload.event.replace("reminder.", "")
        res = await n8n_service.dispatch_reminder(db=db, registration_id=reg.id, reminder_type=rem_type)

    return {
        "status": "success",
        "registration_code": payload.registration_code,
        "event": payload.event,
        "n8n_result": res,
    }
