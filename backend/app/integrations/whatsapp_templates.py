from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from app.core.config import settings


class WhatsAppTemplateType(str, Enum):
    REGISTRATION_CONFIRMATION = "marathon_registration_confirmed"
    PAYMENT_CONFIRMATION = "marathon_payment_confirmed"
    DIGITAL_PASS_BIB = "marathon_digital_pass_bib"
    REMINDER_7_DAYS = "marathon_reminder_7_days"
    REMINDER_1_DAY = "marathon_reminder_1_day"
    REMINDER_EVENT_DAY = "marathon_reminder_event_day"


class WhatsAppTemplateMessage(BaseModel):
    template_name: str
    language_code: str = "en"
    parameters: List[str]
    components: List[Dict[str, Any]]
    rendered_text: str
    recipient_phone: str


class WhatsAppTemplateService:
    """
    Template rendering and validation engine for WhatsApp Business Cloud API.
    Validates required parameters and constructs standard Meta Graph API template payloads.
    """

    # Template definitions with required variables and human-readable text pattern
    TEMPLATES = {
        WhatsAppTemplateType.REGISTRATION_CONFIRMATION: {
            "required_fields": ["participant_name", "registration_code", "category_title"],
            "format": (
                "🎉 *Registration Confirmed!*\n\n"
                "Hello {participant_name},\n\n"
                "Your registration for *{event_name}* is confirmed!\n"
                "• *Registration ID:* {registration_code}\n"
                "• *Race Category:* {category_title}\n"
                "• *Event Date:* {event_date}\n"
                "• *Status:* {status}\n\n"
                "Get ready to run! We will send your official BIB number and digital pass shortly."
            ),
        },
        WhatsAppTemplateType.PAYMENT_CONFIRMATION: {
            "required_fields": ["participant_name", "registration_code", "amount_inr"],
            "format": (
                "💳 *Payment Received!*\n\n"
                "Hello {participant_name},\n\n"
                "We received your payment of *₹{amount_inr:.2f}* for Registration ID *{registration_code}*.\n"
                "• *Payment Status:* {payment_status}\n\n"
                "Thank you for completing your registration!"
            ),
        },
        WhatsAppTemplateType.DIGITAL_PASS_BIB: {
            "required_fields": ["participant_name", "registration_code", "bib_number", "category_title"],
            "format": (
                "🎟️ *Your Digital Entry Pass & BIB Number*\n\n"
                "Hello {participant_name},\n\n"
                "Your official Marathon BIB number is: *{bib_number}*\n"
                "• *Registration ID:* {registration_code}\n"
                "• *Race Category:* {category_title}\n"
                "• *Venue:* {event_venue}\n\n"
                "Please present this entry pass at the Expo counter to collect your race kit."
            ),
        },
        WhatsAppTemplateType.REMINDER_7_DAYS: {
            "required_fields": ["participant_name", "category_title"],
            "format": (
                "⏳ *7 Days to Go! — {event_name}*\n\n"
                "Hello {participant_name},\n\n"
                "Just 1 week remains until race day on *{event_date}*!\n"
                "• *Your Category:* {category_title}\n\n"
                "Remember to hydrate well and taper your training this week. See you at the starting line!"
            ),
        },
        WhatsAppTemplateType.REMINDER_1_DAY: {
            "required_fields": ["participant_name"],
            "format": (
                "🏃 *Race Tomorrow! — Important Instructions*\n\n"
                "Hello {participant_name},\n\n"
                "Tomorrow is the big day (*{event_date}*)!\n"
                "• *Venue:* {event_venue}\n"
                "• *Instructions:* Pin your BIB to your chest shirt, arrive 45 mins before your category flag-off, and carry your digital pass."
            ),
        },
        WhatsAppTemplateType.REMINDER_EVENT_DAY: {
            "required_fields": ["participant_name", "bib_number", "reporting_time"],
            "format": (
                "🏁 *Today is Race Day! — Good Luck!*\n\n"
                "Hello {participant_name},\n\n"
                "It's time to run! Welcome to *{event_name}*.\n"
                "• *Your BIB:* {bib_number}\n"
                "• *Reporting Time:* {reporting_time}\n"
                "• *Venue:* {event_venue}\n\n"
                "Baggage counters and hydration stations are open. Give it your best!"
            ),
        },
    }

    @classmethod
    def render_template(
        cls,
        template_type: WhatsAppTemplateType,
        recipient_phone: str,
        data: Dict[str, Any],
    ) -> WhatsAppTemplateMessage:
        """
        Validate data and render a template into a WhatsAppTemplateMessage object.
        """
        if not recipient_phone or not recipient_phone.strip():
            raise ValueError("Recipient phone number is required to render WhatsApp template.")

        if template_type not in cls.TEMPLATES:
            raise ValueError(f"Unknown WhatsApp template type: {template_type}")

        template_def = cls.TEMPLATES[template_type]
        required_fields = template_def["required_fields"]

        # Validate required variables
        missing = [f for f in required_fields if f not in data or data[f] is None or str(data[f]).strip() == ""]
        if missing:
            raise ValueError(
                f"Missing required fields for template '{template_type.value}': {', '.join(missing)}"
            )

        # Merge defaults
        context = {
            "event_name": settings.EVENT_NAME,
            "event_date": settings.EVENT_DATE,
            "event_venue": settings.EVENT_VENUE,
            "status": "CONFIRMED",
            "payment_status": "SUCCESS",
            **data,
        }

        # Build Meta parameter list
        param_values = []
        if template_type == WhatsAppTemplateType.REGISTRATION_CONFIRMATION:
            param_values = [
                str(context["participant_name"]),
                str(context["registration_code"]),
                str(context["category_title"]),
                str(context["event_name"]),
                str(context["event_date"]),
                str(context["status"]),
            ]
        elif template_type == WhatsAppTemplateType.PAYMENT_CONFIRMATION:
            param_values = [
                str(context["participant_name"]),
                str(context["registration_code"]),
                f"₹{float(context['amount_inr']):.2f}",
                str(context["payment_status"]),
            ]
        elif template_type == WhatsAppTemplateType.DIGITAL_PASS_BIB:
            param_values = [
                str(context["participant_name"]),
                str(context["registration_code"]),
                str(context["bib_number"]),
                str(context["category_title"]),
                str(context["event_venue"]),
            ]
        elif template_type == WhatsAppTemplateType.REMINDER_7_DAYS:
            param_values = [
                str(context["participant_name"]),
                str(context["event_name"]),
                str(context["event_date"]),
                str(context["category_title"]),
            ]
        elif template_type == WhatsAppTemplateType.REMINDER_1_DAY:
            param_values = [
                str(context["participant_name"]),
                str(context["event_date"]),
                str(context["event_venue"]),
            ]
        elif template_type == WhatsAppTemplateType.REMINDER_EVENT_DAY:
            param_values = [
                str(context["participant_name"]),
                str(context["event_name"]),
                str(context["reporting_time"]),
                str(context["event_venue"]),
                str(context["bib_number"]),
            ]

        components = [
            {
                "type": "body",
                "parameters": [{"type": "text", "text": val} for val in param_values],
            }
        ]

        rendered_text = template_def["format"].format(**context)

        return WhatsAppTemplateMessage(
            template_name=template_type.value,
            language_code="en",
            parameters=param_values,
            components=components,
            rendered_text=rendered_text,
            recipient_phone=recipient_phone.strip(),
        )


whatsapp_template_service = WhatsAppTemplateService()
