from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Literal, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.registration import Registration
from app.services.whatsapp_service import whatsapp_service
from app.core.logging import logger

router = APIRouter()


class WhatsAppReminderSimulationRequest(BaseModel):
    reminder_type: Literal["7_days", "1_day", "event_day", "payment_confirmation", "digital_pass"] = Field(
        ..., description="The type of WhatsApp notification/reminder to simulate"
    )


@router.post(
    "/{registration_code}/simulate-whatsapp",
    summary="Simulate WhatsApp Notifications & Pre-Event Reminders (Developer Demo)",
)
async def simulate_whatsapp_notification(
    registration_code: str,
    payload: WhatsAppReminderSimulationRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Developer demonstration endpoint to test WhatsApp notifications & reminders on demand
    without waiting for the actual event date.
    """
    query = select(Registration).where(Registration.registration_code == registration_code)
    result = await db.execute(query)
    reg = result.scalar_one_or_none()

    if not reg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Registration '{registration_code}' not found.",
        )

    res: Dict[str, Any] = {}
    if payload.reminder_type == "7_days":
        res = await whatsapp_service.send_reminder_7_days(db=db, registration_id=reg.id)
    elif payload.reminder_type == "1_day":
        res = await whatsapp_service.send_reminder_1_day(db=db, registration_id=reg.id)
    elif payload.reminder_type == "event_day":
        res = await whatsapp_service.send_reminder_event_day(db=db, registration_id=reg.id)
    elif payload.reminder_type == "payment_confirmation":
        res = await whatsapp_service.send_payment_confirmation(db=db, registration_id=reg.id)
    elif payload.reminder_type == "digital_pass":
        res = await whatsapp_service.send_digital_pass(db=db, registration_id=reg.id)

    return {
        "status": "success",
        "registration_code": registration_code,
        "simulated_type": payload.reminder_type,
        "whatsapp_result": res,
    }
