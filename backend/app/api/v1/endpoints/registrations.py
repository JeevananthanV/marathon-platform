from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.registration import (
    RegistrationInitiateRequest,
    RegistrationInitiateResponse,
    RegistrationDetailResponse,
)
from app.services.registration_service import RegistrationService

router = APIRouter()


@router.post(
    "/initiate",
    response_model=RegistrationInitiateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Initiate marathon registration & generate Razorpay order",
)
async def initiate_registration(
    payload: RegistrationInitiateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Validate runner details, prevent duplicate registrations, capture UTM attribution,
    create PENDING registration (format: MX26-000001), and generate Razorpay TEST MODE order.
    """
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    result = await RegistrationService.initiate_registration(
        db=db,
        payload=payload,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return result


@router.get(
    "/{registration_code}",
    response_model=RegistrationDetailResponse,
    summary="Get registration details & digital pass",
)
async def get_registration(
    registration_code: str,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve verified registration status, allocated BIB number, participant and category info."""
    registration = await RegistrationService.get_registration_by_code(
        db=db, registration_code=registration_code
    )
    if not registration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Registration '{registration_code}' not found.",
        )
    return registration
