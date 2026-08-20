from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.payment import (
    PaymentVerificationRequest,
    PaymentVerificationResponse,
)
from app.services.payment_service import PaymentService

router = APIRouter()


@router.post(
    "/verify",
    response_model=PaymentVerificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Server-side Razorpay payment signature verification",
)
async def verify_payment(
    payload: PaymentVerificationRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Verify payment signature server-side using HMAC SHA256.
    Transitions payment to SUCCESS, confirms registration, and allocates BIB number.
    """
    result = await PaymentService.verify_payment(
        db=db,
        razorpay_order_id=payload.razorpay_order_id,
        razorpay_payment_id=payload.razorpay_payment_id,
        razorpay_signature=payload.razorpay_signature,
    )
    return result
