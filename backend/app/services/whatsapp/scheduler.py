from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from app.models.registration import Registration
from app.models.participant import Participant
from app.services.whatsapp.templates import WhatsAppTemplateType
from app.core.config import settings
from app.core.logging import logger


class ReminderScheduleRule:
    def __init__(self, reminder_type: WhatsAppTemplateType, days_before: int, is_post_event: bool = False, days_after: int = 0):
        self.reminder_type = reminder_type
        self.days_before = days_before
        self.is_post_event = is_post_event
        self.days_after = days_after


DEFAULT_REMINDER_RULES: List[ReminderScheduleRule] = [
    ReminderScheduleRule(WhatsAppTemplateType.REMINDER_7_DAYS, days_before=7),
    ReminderScheduleRule(WhatsAppTemplateType.REMINDER_3_DAYS, days_before=3),
    ReminderScheduleRule(WhatsAppTemplateType.REMINDER_1_DAY, days_before=1),
    ReminderScheduleRule(WhatsAppTemplateType.REMINDER_RACE_DAY, days_before=0),
    ReminderScheduleRule(WhatsAppTemplateType.POST_EVENT_THANKS, days_before=0, is_post_event=True, days_after=1),
]


class ReminderSchedulerService:
    """
    Evaluates due marathon reminders and triggers idempotent WhatsApp notifications.
    Can be invoked periodically by Cron, Celery, or n8n automation webhook.
    """

    @classmethod
    async def process_due_reminders(
        cls,
        db: AsyncSession,
        reference_date: Optional[date] = None,
        force_reminder_type: Optional[WhatsAppTemplateType] = None,
        limit: int = 200,
    ) -> Dict[str, Any]:
        """
        Scan confirmed registrations and dispatch eligible, non-sent marathon reminders.
        """
        from app.services.whatsapp.service import whatsapp_service

        today = reference_date or datetime.now(timezone.utc).date()
        results: List[Dict[str, Any]] = []
        sent_count = 0
        skipped_count = 0
        failed_count = 0

        # Query all CONFIRMED registrations with participant consent
        query = (
            select(Registration)
            .join(Registration.participant)
            .options(
                selectinload(Registration.participant),
                selectinload(Registration.category),
                selectinload(Registration.payments),
            )
            .where(
                and_(
                    Registration.status == "CONFIRMED",
                    Registration.communication_consent == True,
                    Participant.whatsapp_consent == True,
                )
            )
            .limit(limit)
        )
        res = await db.execute(query)
        confirmed_registrations = res.scalars().all()

        for reg in confirmed_registrations:
            rules_to_evaluate = [r for r in DEFAULT_REMINDER_RULES] if not force_reminder_type else [
                r for r in DEFAULT_REMINDER_RULES if r.reminder_type == force_reminder_type
            ]

            for rule in rules_to_evaluate:
                # Dispatch the reminder through WhatsApp service
                dispatch_res = await whatsapp_service.send_reminder(
                    db=db,
                    registration_id=reg.id,
                    template_type=rule.reminder_type,
                )

                if dispatch_res.get("status") == "SUCCESS":
                    if dispatch_res.get("idempotent"):
                        skipped_count += 1
                    else:
                        sent_count += 1
                else:
                    failed_count += 1

                results.append({
                    "registration_code": reg.registration_code,
                    "reminder_type": rule.reminder_type.value,
                    "result": dispatch_res,
                })

        logger.info(
            f"[REMINDER SCHEDULER] Evaluated {len(confirmed_registrations)} runners: "
            f"{sent_count} sent, {skipped_count} skipped (idempotent), {failed_count} failed."
        )

        return {
            "status": "success",
            "total_evaluated": len(confirmed_registrations),
            "sent_count": sent_count,
            "skipped_count": skipped_count,
            "failed_count": failed_count,
            "details": results,
        }


reminder_scheduler = ReminderSchedulerService()
