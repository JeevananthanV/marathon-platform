import re
from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel


class WhatsAppTemplateType(str, Enum):
    REGISTRATION_CONFIRMATION = "marathon_registration_confirmed"
    PAYMENT_CONFIRMATION = "marathon_payment_confirmed"
    DIGITAL_PASS_BIB = "marathon_digital_pass_bib"
    REMINDER_7_DAYS = "marathon_reminder_7_days"
    REMINDER_3_DAYS = "marathon_reminder_3_days"
    REMINDER_1_DAY = "marathon_reminder_1_day"
    REMINDER_RACE_DAY = "marathon_reminder_event_day"
    POST_EVENT_THANKS = "marathon_post_event_thanks"


# Default Template Content Specifications with Named Placeholders
TEMPLATE_DEFINITIONS: Dict[WhatsAppTemplateType, Dict[str, Any]] = {
    WhatsAppTemplateType.REGISTRATION_CONFIRMATION: {
        "title": "Marathon Registration Initiated",
        "body_text": (
            "Hi {{name}}! 🏃‍♂️ Your registration for {{category}} at {{event_name}} is initiated. "
            "Registration ID: {{registration_id}}. Status: {{payment_status}}. "
            "Event Date: {{event_date}} at {{venue}}. "
            "Support: {{support_contact}}."
        ),
        "required_fields": ["name", "registration_id", "category", "event_date", "venue", "payment_status"],
    },
    WhatsAppTemplateType.PAYMENT_CONFIRMATION: {
        "title": "Marathon Payment Confirmed",
        "body_text": (
            "🎉 Congratulations {{name}}! Your payment of ₹{{amount}} for {{category}} is confirmed. "
            "BIB Number: {{bib_number}} | Reg Code: {{registration_id}}. "
            "Event Date: {{event_date}} | Venue: {{venue}} | Reporting: {{reporting_time}}. "
            "See you at the starting line!"
        ),
        "required_fields": ["name", "amount", "category", "bib_number", "registration_id", "event_date", "venue"],
    },
    WhatsAppTemplateType.DIGITAL_PASS_BIB: {
        "title": "Digital Race Pass & BIB Card",
        "body_text": (
            "🎫 Here is your official Digital Race Pass, {{name}}! "
            "BIB: {{bib_number}} | Category: {{category}} | Start: {{reporting_time}}. "
            "Venue: {{venue}} on {{event_date}}."
        ),
        "required_fields": ["name", "category", "bib_number", "event_date", "venue"],
    },
    WhatsAppTemplateType.REMINDER_7_DAYS: {
        "title": "7 Days to Race Day",
        "body_text": (
            "Hi {{name}}! 7 days left until {{event_name}}! ⏳ "
            "Category: {{category}} | BIB: {{bib_number}}. "
            "Event Date: {{event_date}} at {{venue}}. "
            "Start tapering your runs and stay hydrated!"
        ),
        "required_fields": ["name", "category", "bib_number", "event_date", "venue"],
    },
    WhatsAppTemplateType.REMINDER_3_DAYS: {
        "title": "3 Days to Race Day - Expo Alert",
        "body_text": (
            "Hi {{name}}! 3 days to go! 🏃 "
            "Don't forget to collect your race kit & BIB ({{bib_number}}) from the Expo. "
            "Race Date: {{event_date}} | Venue: {{venue}}."
        ),
        "required_fields": ["name", "bib_number", "event_date", "venue"],
    },
    WhatsAppTemplateType.REMINDER_1_DAY: {
        "title": "Tomorrow is Race Day!",
        "body_text": (
            "Get ready {{name}}! Tomorrow is race day for {{category}}! 🌟 "
            "BIB: {{bib_number}} | Venue: {{venue}} | Reporting Time: {{reporting_time}}. "
            "Get a good night's sleep and remember to pin your BIB on your chest."
        ),
        "required_fields": ["name", "category", "bib_number", "venue", "reporting_time"],
    },
    WhatsAppTemplateType.REMINDER_RACE_DAY: {
        "title": "Race Morning Alert",
        "body_text": (
            "Good morning {{name}}! It's Race Day! 🏁 "
            "Reporting Time: {{reporting_time}} for {{category}}. "
            "Venue: {{venue}} | BIB: {{bib_number}}. "
            "Run strong and enjoy every kilometer!"
        ),
        "required_fields": ["name", "reporting_time", "category", "venue", "bib_number"],
    },
    WhatsAppTemplateType.POST_EVENT_THANKS: {
        "title": "Post-Event Thank You & Finisher Timing",
        "body_text": (
            "Congratulations {{name}} on completing the {{category}}! 🏅 "
            "BIB: {{bib_number}}. Thank you for being a part of {{event_name}}! "
            "Your official timing and finisher certificate are available now."
        ),
        "required_fields": ["name", "category", "bib_number"],
    },
}


class RenderedWhatsAppMessage(BaseModel):
    template_type: WhatsAppTemplateType
    template_name: str
    recipient_phone: str
    rendered_text: str
    parameters: List[Dict[str, Any]]
    components: List[Dict[str, Any]]
    context_data: Dict[str, Any]


class WhatsAppTemplateEngine:
    """
    Template compilation, parameter binding, and formatting engine for WhatsApp messages.
    """

    @classmethod
    def render_template(
        cls,
        template_type: WhatsAppTemplateType,
        recipient_phone: str,
        context: Dict[str, Any],
    ) -> RenderedWhatsAppMessage:
        """
        Renders a template message with variable interpolation and parameters structure.
        """
        definition = TEMPLATE_DEFINITIONS.get(template_type)
        if not definition:
            raise ValueError(f"Unknown template type: {template_type}")

        # Check required fields
        missing_fields = [f for f in definition["required_fields"] if f not in context or context[f] is None or context[f] == ""]
        if missing_fields:
            raise ValueError(f"Template '{template_type.value}' missing required fields: {', '.join(missing_fields)}")

        body_raw = definition["body_text"]
        
        # Format variables into rendered text
        rendered_text = body_raw
        for key, val in context.items():
            pattern = re.compile(rf"\{{\{{\s*{re.escape(key)}\s*\}}\}}")
            rendered_text = pattern.sub(str(val), rendered_text)

        # Meta Graph API parameter list
        parameters = [{"type": "text", "text": str(context.get(k, ""))} for k in definition["required_fields"]]
        components = [
            {
                "type": "body",
                "parameters": parameters,
            }
        ]

        return RenderedWhatsAppMessage(
            template_type=template_type,
            template_name=template_type.value,
            recipient_phone=recipient_phone,
            rendered_text=rendered_text,
            parameters=parameters,
            components=components,
            context_data=context,
        )


template_engine = WhatsAppTemplateEngine()
