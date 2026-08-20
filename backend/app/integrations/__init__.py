from app.integrations.base import BaseIntegration
from app.integrations.razorpay_client import razorpay_client, RazorpayIntegrationClient
from app.integrations.zoho_crm import zoho_client, ZohoCRMIntegrationClient
from app.integrations.whatsapp_cloud import whatsapp_client, WhatsAppIntegrationClient
from app.integrations.n8n import n8n_client, N8NIntegrationClient
from app.integrations.meta_capi import meta_capi_client, MetaCAPIIntegrationClient

__all__ = [
    "BaseIntegration",
    "razorpay_client",
    "RazorpayIntegrationClient",
    "zoho_client",
    "ZohoCRMIntegrationClient",
    "whatsapp_client",
    "WhatsAppIntegrationClient",
    "n8n_client",
    "N8NIntegrationClient",
    "meta_capi_client",
    "MetaCAPIIntegrationClient",
]
