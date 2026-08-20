from fastapi import APIRouter
from app.api.v1.endpoints import (
    health,
    categories,
    registrations,
    payments,
    webhooks,
    whatsapp_demo,
    whatsapp,
    automation,
    meta_events,
    admin,
)

api_router = APIRouter()

# Health router
api_router.include_router(health.router, prefix="", tags=["Health"])

# Race Categories
api_router.include_router(categories.router, prefix="/categories", tags=["Race Categories"])

# Registrations
api_router.include_router(registrations.router, prefix="/registrations", tags=["Registrations"])

# Payments
api_router.include_router(payments.router, prefix="/payments", tags=["Payments"])

# Webhooks
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])

# WhatsApp Automation & Reminders
api_router.include_router(whatsapp.router, prefix="/whatsapp", tags=["WhatsApp Automation"])

# WhatsApp Simulation & Demo
api_router.include_router(whatsapp_demo.router, prefix="/notifications", tags=["WhatsApp Notifications"])

# n8n Automation Engine
api_router.include_router(automation.router, prefix="/automation", tags=["n8n Automation"])

# Meta Conversions API (CAPI)
api_router.include_router(meta_events.router, prefix="/meta", tags=["Meta CAPI Tracking"])

# Admin & Operations
api_router.include_router(admin.router, prefix="/admin", tags=["Admin & Operations"])
