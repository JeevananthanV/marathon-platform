from typing import Optional, Dict, Any
from datetime import date
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.api.deps import verify_admin_auth
from app.services.whatsapp import reminder_scheduler, WhatsAppTemplateType

router = APIRouter()


@router.post(
    "/reminders/process-due",
    status_code=status.HTTP_200_OK,
    summary="Process and Dispatch Due WhatsApp Marathon Reminders",
)
async def process_due_reminders(
    reference_date: Optional[str] = Query(None, description="Simulate date (YYYY-MM-DD) for testing"),
    reminder_type: Optional[str] = Query(None, description="Force specific reminder type e.g. REMINDER_7_DAYS"),
    limit: int = Query(200, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(verify_admin_auth),
) -> Dict[str, Any]:
    """
    Trigger marathon reminders for all eligible confirmed participants with active consent.
    Can be invoked automatically by n8n workflow or recurring cron scheduler.
    """
    parsed_date = None
    if reference_date:
        try:
            parsed_date = date.fromisoformat(reference_date)
        except ValueError:
            pass

    forced_type = None
    if reminder_type:
        try:
            forced_type = WhatsAppTemplateType[reminder_type.upper()]
        except KeyError:
            try:
                forced_type = WhatsAppTemplateType(reminder_type.lower())
            except ValueError:
                pass

    return await reminder_scheduler.process_due_reminders(
        db=db,
        reference_date=parsed_date,
        force_reminder_type=forced_type,
        limit=limit,
    )
