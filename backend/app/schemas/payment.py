from pydantic import BaseModel, Field


class PaymentVerificationRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


class PaymentVerificationResponse(BaseModel):
    status: str = Field(description="CONFIRMED or FAILED")
    registration_code: str
    bib_number: str
    participant_name: str
    category_title: str
    message: str
