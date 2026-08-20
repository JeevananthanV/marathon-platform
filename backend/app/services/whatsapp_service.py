# Backward compatibility layer for legacy imports of whatsapp_service
from app.services.whatsapp import (
    WhatsAppService,
    whatsapp_service,
    WhatsAppTemplateType,
    delivery_handler,
    reminder_scheduler,
)

__all__ = [
    "WhatsAppService",
    "whatsapp_service",
    "WhatsAppTemplateType",
    "delivery_handler",
    "reminder_scheduler",
]
