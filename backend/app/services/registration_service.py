import uuid
from datetime import datetime, timezone
from typing import Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.models.race_category import RaceCategory
from app.models.participant import Participant
from app.models.registration import Registration
from app.models.payment import Payment
from app.schemas.registration import RegistrationInitiateRequest
from app.integrations.razorpay_client import razorpay_client
from app.core.config import settings
from app.core.logging import logger


async def generate_next_registration_code(db: AsyncSession) -> str:
    """
    Generate unique server-side registration ID in format: MX26-000001
    """
    count_query = select(func.count(Registration.id))
    result = await db.execute(count_query)
    total_registrations = result.scalar_one() or 0
    next_num = total_registrations + 1
    
    # Format MX26-000001 with 6 padded digits
    code = f"MX26-{next_num:06d}"
    
    # Double check uniqueness in case of deleted records
    while True:
        check_query = select(Registration).where(Registration.registration_code == code)
        check_res = await db.execute(check_query)
        if not check_res.scalar_one_or_none():
            break
        next_num += 1
        code = f"MX26-{next_num:06d}"
        
    return code


async def allocate_bib_number(db: AsyncSession, category: RaceCategory) -> str:
    """
    Allocate sequential bib number based on category prefix (e.g. HM-1001, 10K-1001, 5K-1001).
    """
    prefix = category.bib_prefix or category.code
    base_number = 1000 + category.current_count + 1
    bib = f"{prefix}-{base_number}"
    
    while True:
        check_query = select(Registration).where(Registration.bib_number == bib)
        check_res = await db.execute(check_query)
        if not check_res.scalar_one_or_none():
            break
        base_number += 1
        bib = f"{prefix}-{base_number}"
        
    return bib


class RegistrationService:

    @staticmethod
    async def initiate_registration(
        db: AsyncSession,
        payload: RegistrationInitiateRequest,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> dict:
        """
        Validate participant details, prevent duplicate registrations, create PENDING registration,
        and generate Razorpay TEST MODE order.
        """
        # 1. Fetch & Validate Race Category
        cat_query = select(RaceCategory).where(
            and_(RaceCategory.id == payload.category_id, RaceCategory.is_active == True)
        )
        cat_result = await db.execute(cat_query)
        category = cat_result.scalar_one_or_none()
        
        if not category:
            # Also try matching by code (e.g. '5K', '10K', '21K')
            code_query = select(RaceCategory).where(
                and_(RaceCategory.code == payload.category_id, RaceCategory.is_active == True)
            )
            code_result = await db.execute(code_query)
            category = code_result.scalar_one_or_none()

        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Race category '{payload.category_id}' not found or is currently inactive.",
            )

        # Check category capacity
        if category.current_count >= category.max_capacity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Sorry, slots for {category.title} are completely full.",
            )

        # 2. Find or Create Participant
        part_data = payload.participant
        part_query = select(Participant).where(
            (Participant.email == part_data.email) | (Participant.phone_number == part_data.phone_number)
        )
        part_result = await db.execute(part_query)
        participant = part_result.scalar_one_or_none()

        if not participant:
            participant = Participant(
                id=str(uuid.uuid4()),
                full_name=part_data.full_name,
                email=part_data.email,
                phone_number=part_data.phone_number,
                date_of_birth=part_data.date_of_birth,
                gender=part_data.gender,
                blood_group=part_data.blood_group,
                tshirt_size=part_data.tshirt_size,
                emergency_contact_name=part_data.emergency_contact_name,
                emergency_contact_phone=part_data.emergency_contact_phone,
                city=part_data.city,
                state=part_data.state,
                lead_status="PAYMENT_PENDING",
            )
            db.add(participant)
            await db.flush()
        else:
            # Update latest contact / medical info
            participant.full_name = part_data.full_name
            participant.blood_group = part_data.blood_group
            participant.tshirt_size = part_data.tshirt_size
            participant.emergency_contact_name = part_data.emergency_contact_name
            participant.emergency_contact_phone = part_data.emergency_contact_phone
            participant.city = part_data.city
            participant.state = part_data.state
            if participant.lead_status != "CONVERTED":
                participant.lead_status = "PAYMENT_PENDING"
            await db.flush()

        # 3. Duplicate Registration Check
        # Check if participant already has a CONFIRMED registration for this category
        dup_query = select(Registration).where(
            and_(
                Registration.participant_id == participant.id,
                Registration.category_id == category.id,
                Registration.status == "CONFIRMED",
            )
        )
        dup_result = await db.execute(dup_query)
        if dup_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Participant ({part_data.email}) is already registered and confirmed for {category.title}.",
            )

        # 4. Generate unique Registration Code (Format: MX26-000001)
        registration_code = await generate_next_registration_code(db)

        # 5. Extract UTM Attribution Parameters
        utm = payload.utm
        utm_source = utm.utm_source if utm else None
        utm_medium = utm.utm_medium if utm else None
        utm_campaign = utm.utm_campaign if utm else None
        utm_term = utm.utm_term if utm else None
        utm_content = utm.utm_content if utm else None
        referrer = utm.referrer if utm else None

        # 6. Create PENDING Registration
        registration = Registration(
            id=str(uuid.uuid4()),
            registration_code=registration_code,
            participant_id=participant.id,
            category_id=category.id,
            status="PENDING",
            utm_source=utm_source,
            utm_medium=utm_medium,
            utm_campaign=utm_campaign,
            utm_term=utm_term,
            utm_content=utm_content,
            referrer=referrer,
            ip_address=ip_address,
            user_agent=user_agent,
            terms_accepted=True,
            communication_consent=True,
        )
        db.add(registration)
        await db.flush()

        # 7. Create Razorpay Server-Side Order
        amount_inr = float(category.price_inr)
        order_notes = {
            "registration_code": registration_code,
            "category_code": category.code,
            "participant_name": participant.full_name,
            "email": participant.email,
        }
        
        rzp_order = razorpay_client.create_order(
            amount_inr=amount_inr,
            receipt=registration_code,
            notes=order_notes,
        )
        razorpay_order_id = rzp_order.get("id")

        # 8. Create Payment Record (PENDING)
        payment = Payment(
            id=str(uuid.uuid4()),
            registration_id=registration.id,
            razorpay_order_id=razorpay_order_id,
            amount_inr=amount_inr,
            currency="INR",
            status="PENDING",
        )
        db.add(payment)
        await db.commit()

        logger.info(
            f"Registration initiated: {registration_code} | Participant: {participant.email} | "
            f"Category: {category.code} | Razorpay Order: {razorpay_order_id}"
        )

        # 9. Non-blocking Zoho CRM Lead Synchronization (Phase 5)
        try:
            from app.services.zoho_service import zoho_service
            await zoho_service.sync_registration_to_zoho(db=db, registration_id=registration.id)
        except Exception as zoho_err:
            logger.error(f"[Registration -> Zoho] Non-fatal Zoho sync exception: {str(zoho_err)}")

        return {
            "registration_id": registration.id,
            "registration_code": registration_code,
            "razorpay_order_id": razorpay_order_id,
            "amount_inr": amount_inr,
            "currency": "INR",
            "razorpay_key_id": settings.RAZORPAY_KEY_ID,
        }

    @staticmethod
    async def get_registration_by_code(db: AsyncSession, registration_code: str) -> Optional[Registration]:
        """Fetch registration with participant and category eagerly loaded."""
        from sqlalchemy.orm import selectinload
        query = (
            select(Registration)
            .options(
                selectinload(Registration.participant),
                selectinload(Registration.category),
                selectinload(Registration.payments),
            )
            .where(Registration.registration_code == registration_code)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()
