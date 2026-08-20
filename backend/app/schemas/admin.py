from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


VALID_LEAD_STATUSES = ["NEW", "CONTACTED", "REGISTERED", "PAYMENT_PENDING", "CONVERTED", "LOST"]


class LeadStatusUpdateRequest(BaseModel):
    status: str = Field(..., description="Target lead status")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        clean_status = v.strip().upper()
        if clean_status not in VALID_LEAD_STATUSES:
            raise ValueError(
                f"Invalid lead status '{v}'. Allowed statuses are: {', '.join(VALID_LEAD_STATUSES)}"
            )
        return clean_status


class CategoryMetricItem(BaseModel):
    code: str
    title: str
    max_capacity: int
    current_count: int
    slots_remaining: int
    fill_percentage: float
    paid_count: int
    price_inr: float
    revenue_inr: float


class AdminDashboardStats(BaseModel):
    event_name: str
    total_leads: int
    total_registrations: int
    paid_registrations: int
    pending_payments: int
    failed_payments: int
    revenue_inr: float
    average_order_value_inr: float
    paid_participants_count: int
    categories: List[CategoryMetricItem]
    recent_registrations: List[Dict[str, Any]]
    integrations_summary: Dict[str, Any]
    zoho_summary: Optional[Dict[str, Any]] = None
    whatsapp_summary: Optional[Dict[str, Any]] = None


class AdminLeadItem(BaseModel):
    id: str
    name: str
    email: str
    phone: str
    city: str
    state: str
    category_code: Optional[str] = None
    category_title: Optional[str] = None
    lead_status: str
    whatsapp_consent: Optional[bool] = True
    payment_status: str
    registration_status: str
    registration_code: Optional[str] = None
    amount_inr: float = 0.0
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    zoho_sync_status: Optional[str] = "PENDING"
    zoho_lead_id: Optional[str] = None
    created_at: str


class AdminLeadsResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[AdminLeadItem]


class AdminRegistrationItem(BaseModel):
    registration_id: str
    registration_code: str
    bib_number: Optional[str] = None
    status: str
    category_code: str
    category_title: str
    participant_name: str
    email: str
    phone: str
    city: str
    amount_inr: float
    payment_status: str
    razorpay_payment_id: Optional[str] = None
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    zoho_sync_status: Optional[str] = "PENDING"
    zoho_lead_id: Optional[str] = None
    zoho_last_sync_attempt: Optional[str] = None
    created_at: str
    confirmed_at: Optional[str] = None


class AdminRegistrationsResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[AdminRegistrationItem]


class FunnelMetrics(BaseModel):
    total_leads: int
    total_registered: int
    total_paid: int
    lead_to_reg_rate_pct: float
    reg_to_paid_rate_pct: float
    overall_conversion_rate_pct: float


class UtmSourceAnalytics(BaseModel):
    source: str
    leads_count: int
    registered_count: int
    paid_count: int
    conversion_rate_pct: float
    revenue_inr: float


class CategoryAnalytics(BaseModel):
    category_code: str
    category_title: str
    registered_count: int
    paid_count: int
    revenue_inr: float
    share_pct: float


class RevenueMetrics(BaseModel):
    total_revenue_inr: float
    paid_participants_count: int
    average_order_value_inr: float


class AdminAnalyticsResponse(BaseModel):
    funnel: FunnelMetrics
    categories: List[CategoryAnalytics]
    utm_sources: List[UtmSourceAnalytics]
    revenue: RevenueMetrics


class ZohoStatusSummary(BaseModel):
    mode: str
    configured: bool
    status: str
    synced_count: int
    pending_count: int
    failed_count: int
    last_sync_attempt: Optional[str] = None
    health: Dict[str, Any]


class ZohoSyncResponse(BaseModel):
    status: str
    registration_code: Optional[str] = None
    zoho_record_id: Optional[str] = None
    action: Optional[str] = None
    mock: Optional[bool] = None
    error: Optional[str] = None


class ZohoRetryResponse(BaseModel):
    total_processed: int
    successful: int
    failed: int
    details: List[Dict[str, Any]]


# Phase 6 WhatsApp Communication Schemas
class WhatsAppStatsSummary(BaseModel):
    total_messages: int
    pending_count: int
    sent_count: int
    delivered_count: int
    read_count: int
    failed_count: int
    provider_health: Dict[str, Any]


class WhatsAppMessageItem(BaseModel):
    id: str
    registration_id: Optional[str] = None
    participant_id: Optional[str] = None
    phone_number: str
    message_type: str
    template_name: str
    message_content: Optional[str] = None
    provider: str
    provider_message_id: Optional[str] = None
    idempotency_key: str
    status: str
    created_at: str
    sent_at: Optional[str] = None
    delivered_at: Optional[str] = None
    read_at: Optional[str] = None
    failed_at: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0


class WhatsAppMessageListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[WhatsAppMessageItem]


class WhatsAppRetryResponse(BaseModel):
    total_processed: int
    successful: int
    failed: int
    details: List[Dict[str, Any]]
