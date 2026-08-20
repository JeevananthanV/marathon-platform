from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.participant import ParticipantCreate, ParticipantResponse
from app.schemas.race_category import RaceCategoryResponse


class UTMParameters(BaseModel):
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    utm_term: Optional[str] = None
    utm_content: Optional[str] = None
    referrer: Optional[str] = None


class RegistrationInitiateRequest(BaseModel):
    category_id: str = Field(..., description="Race Category ID or Code (e.g. 5K, 10K, 21K)")
    participant: ParticipantCreate
    utm: Optional[UTMParameters] = None
    terms_accepted: bool = Field(default=True, description="Consent to terms and conditions")
    communication_consent: bool = Field(default=True, description="Consent to race updates and alerts")


class RegistrationInitiateResponse(BaseModel):
    registration_id: str
    registration_code: str
    razorpay_order_id: str
    amount_inr: float
    currency: str = "INR"
    razorpay_key_id: str


class RegistrationDetailResponse(BaseModel):
    id: str
    registration_code: str
    status: str
    bib_number: Optional[str] = None
    confirmed_at: Optional[datetime] = None
    created_at: datetime
    participant: ParticipantResponse
    category: RaceCategoryResponse

    model_config = ConfigDict(from_attributes=True)
