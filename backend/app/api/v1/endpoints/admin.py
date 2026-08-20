import csv
import io
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, asc, delete
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.api.deps import verify_admin_auth
from app.models.registration import Registration
from app.models.payment import Payment
from app.models.participant import Participant
from app.models.race_category import RaceCategory
from app.models.integration_log import IntegrationLog
from app.services.zoho_service import zoho_service
from app.services.whatsapp import whatsapp_service
from app.schemas.admin import (
    AdminDashboardStats,
    AdminLeadsResponse,
    AdminLeadItem,
    LeadStatusUpdateRequest,
    AdminRegistrationsResponse,
    AdminRegistrationItem,
    AdminAnalyticsResponse,
    FunnelMetrics,
    CategoryAnalytics,
    UtmSourceAnalytics,
    RevenueMetrics,
    CategoryMetricItem,
    ZohoStatusSummary,
    ZohoSyncResponse,
    ZohoRetryResponse,
    WhatsAppStatsSummary,
    WhatsAppMessageListResponse,
    WhatsAppMessageItem,
    WhatsAppRetryResponse,
)
from app.core.config import settings
from app.core.logging import logger

router = APIRouter()


@router.get(
    "/overview",
    summary="Operations Dashboard Overview Metrics (Backward Compatible)",
)
async def get_operations_overview(
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(verify_admin_auth),
) -> Dict[str, Any]:
    """Returns high-level statistics for event operations overview."""
    total_reg = (await db.execute(select(func.count(Registration.id)))).scalar_one() or 0
    confirmed_reg = (
        await db.execute(select(func.count(Registration.id)).where(Registration.status == "CONFIRMED"))
    ).scalar_one() or 0
    pending_reg = (
        await db.execute(select(func.count(Registration.id)).where(Registration.status == "PENDING"))
    ).scalar_one() or 0

    total_payments = (await db.execute(select(func.count(Payment.id)))).scalar_one() or 0
    successful_payments = (
        await db.execute(select(func.count(Payment.id)).where(Payment.status == "SUCCESS"))
    ).scalar_one() or 0
    failed_payments = (
        await db.execute(select(func.count(Payment.id)).where(Payment.status == "FAILED"))
    ).scalar_one() or 0
    revenue_inr = (
        await db.execute(select(func.sum(Payment.amount_inr)).where(Payment.status == "SUCCESS"))
    ).scalar_one() or 0.0

    categories = (await db.execute(select(RaceCategory))).scalars().all()
    category_metrics = [
        {
            "code": c.code,
            "title": c.title,
            "max_capacity": c.max_capacity,
            "max_slots": c.max_capacity,
            "current_count": c.current_count,
            "price_inr": float(c.price_inr),
        }
        for c in categories
    ]

    log_query = select(
        IntegrationLog.service_name,
        IntegrationLog.status,
        func.count(IntegrationLog.id),
    ).group_by(IntegrationLog.service_name, IntegrationLog.status)
    log_res = await db.execute(log_query)
    integration_stats = {}
    for service, stat, count in log_res.all():
        if service not in integration_stats:
            integration_stats[service] = {"SUCCESS": 0, "FAILED": 0}
        integration_stats[service][stat] = count

    return {
        "event_name": settings.EVENT_NAME,
        "registrations": {
            "total": total_reg,
            "confirmed": confirmed_reg,
            "pending": pending_reg,
        },
        "payments": {
            "total_transactions": total_payments,
            "successful": successful_payments,
            "failed": failed_payments,
            "total_revenue_inr": float(revenue_inr),
        },
        "categories": category_metrics,
        "integrations": integration_stats,
    }


@router.get(
    "/dashboard",
    response_model=AdminDashboardStats,
    summary="Dashboard Overview KPIs and Real Database Metrics",
)
async def get_admin_dashboard(
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(verify_admin_auth),
) -> AdminDashboardStats:
    """
    Returns real-time dashboard metrics calculated directly from database tables:
    - Total leads, registrations, confirmed, pending, failed
    - Actual verified revenue & average order value
    - Category capacity, slot utilization, and per-category revenue
    - Recent registrations list
    - Zoho CRM synchronization summary
    """
    # 1. Total Leads & Registrations
    total_leads = (await db.execute(select(func.count(Participant.id)))).scalar_one() or 0
    total_reg = (await db.execute(select(func.count(Registration.id)))).scalar_one() or 0
    confirmed_reg = (
        await db.execute(select(func.count(Registration.id)).where(Registration.status == "CONFIRMED"))
    ).scalar_one() or 0
    pending_reg = (
        await db.execute(select(func.count(Registration.id)).where(Registration.status == "PENDING"))
    ).scalar_one() or 0
    failed_payments = (
        await db.execute(select(func.count(Payment.id)).where(Payment.status == "FAILED"))
    ).scalar_one() or 0

    # 2. Verified Revenue (Only SUCCESS payments)
    revenue_res = await db.execute(
        select(
            func.coalesce(func.sum(Payment.amount_inr), 0.0),
            func.count(Payment.id),
        ).where(Payment.status == "SUCCESS")
    )
    total_revenue_inr, paid_participants_count = revenue_res.one()
    total_revenue_inr = float(total_revenue_inr or 0.0)
    paid_participants_count = int(paid_participants_count or 0)
    aov = round(total_revenue_inr / paid_participants_count, 2) if paid_participants_count > 0 else 0.0

    # 3. Category Metrics
    categories = (await db.execute(select(RaceCategory).order_by(RaceCategory.distance_km.asc()))).scalars().all()
    cat_items: List[CategoryMetricItem] = []
    
    for c in categories:
        cat_paid_count = (
            await db.execute(
                select(func.count(Registration.id)).where(
                    and_(Registration.category_id == c.id, Registration.status == "CONFIRMED")
                )
            )
        ).scalar_one() or 0
        
        cat_revenue = float(cat_paid_count * float(c.price_inr))
        slots_rem = max(0, c.max_capacity - c.current_count)
        fill_pct = round((c.current_count / c.max_capacity) * 100, 1) if c.max_capacity > 0 else 0.0
        
        cat_items.append(
            CategoryMetricItem(
                code=c.code,
                title=c.title,
                max_capacity=c.max_capacity,
                current_count=c.current_count,
                slots_remaining=slots_rem,
                fill_percentage=fill_pct,
                paid_count=cat_paid_count,
                price_inr=float(c.price_inr),
                revenue_inr=cat_revenue,
            )
        )

    # 4. Recent Registrations
    recent_query = (
        select(Registration)
        .options(
            selectinload(Registration.participant),
            selectinload(Registration.category),
            selectinload(Registration.payments),
        )
        .order_by(Registration.created_at.desc())
        .limit(10)
    )
    recent_records = (await db.execute(recent_query)).scalars().all()
    recent_list = []
    for r in recent_records:
        payment = r.payments[0] if r.payments else None
        recent_list.append({
            "registration_id": r.id,
            "registration_code": r.registration_code,
            "bib_number": r.bib_number,
            "status": r.status,
            "category": r.category.title if r.category else None,
            "category_code": r.category.code if r.category else None,
            "participant_name": r.participant.full_name if r.participant else "Runner",
            "email": r.participant.email if r.participant else "",
            "phone": r.participant.phone_number if r.participant else "",
            "amount_inr": float(payment.amount_inr) if payment else (float(r.category.price_inr) if r.category else 0.0),
            "payment_status": payment.status if payment else "NONE",
            "zoho_sync_status": r.zoho_sync_status or "PENDING",
            "created_at": r.created_at.isoformat() if r.created_at else "",
        })

    # 5. Integration Health Summary
    log_query = select(
        IntegrationLog.service_name,
        IntegrationLog.status,
        func.count(IntegrationLog.id),
    ).group_by(IntegrationLog.service_name, IntegrationLog.status)
    log_res = await db.execute(log_query)
    integration_stats = {}
    for service, stat, count in log_res.all():
        if service not in integration_stats:
            integration_stats[service] = {"SUCCESS": 0, "FAILED": 0}
        integration_stats[service][stat] = count

    # 6. Zoho CRM Summary
    zoho_summary = await zoho_service.get_zoho_status_summary(db=db)

    # 7. WhatsApp Communication Summary (Phase 6)
    whatsapp_summary = await whatsapp_service.get_communication_stats(db=db)

    return AdminDashboardStats(
        event_name=settings.EVENT_NAME,
        total_leads=total_leads,
        total_registrations=total_reg,
        paid_registrations=confirmed_reg,
        pending_payments=pending_reg,
        failed_payments=failed_payments,
        revenue_inr=total_revenue_inr,
        average_order_value_inr=aov,
        paid_participants_count=paid_participants_count,
        categories=cat_items,
        recent_registrations=recent_list,
        integrations_summary=integration_stats,
        zoho_summary=zoho_summary,
        whatsapp_summary=whatsapp_summary,
    )


@router.get(
    "/zoho/status",
    response_model=ZohoStatusSummary,
    summary="Get Zoho CRM Integration and Synchronization Status",
)
async def get_zoho_sync_status(
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(verify_admin_auth),
) -> ZohoStatusSummary:
    """Returns Zoho CRM sync metrics, health, mode, and pending/failed counts."""
    summary = await zoho_service.get_zoho_status_summary(db=db)
    return ZohoStatusSummary(**summary)


@router.post(
    "/zoho/sync/{registration_id}",
    response_model=ZohoSyncResponse,
    summary="Manually Trigger Zoho Synchronization for Specific Registration",
)
async def manual_zoho_sync_registration(
    registration_id: str,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(verify_admin_auth),
) -> ZohoSyncResponse:
    """Manually trigger Zoho CRM synchronization for a single registration."""
    res = await zoho_service.sync_registration_to_zoho(db=db, registration_id=registration_id)
    if res.get("status") == "FAILED" and res.get("error") == "Registration not found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Registration '{registration_id}' not found.")
    return ZohoSyncResponse(**res)


@router.post(
    "/zoho/retry-failed",
    response_model=ZohoRetryResponse,
    summary="Retry All Failed or Pending Zoho Synchronizations",
)
async def retry_failed_zoho_syncs(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(verify_admin_auth),
) -> ZohoRetryResponse:
    """Retries all pending or failed Zoho CRM synchronizations."""
    reports = await zoho_service.retry_failed_zoho_syncs(db=db, limit=limit)
    successful = sum(1 for r in reports if r.get("status") == "SUCCESS")
    failed = sum(1 for r in reports if r.get("status") == "FAILED")
    return ZohoRetryResponse(
        total_processed=len(reports),
        successful=successful,
        failed=failed,
        details=reports,
    )


# Phase 6 WhatsApp Communication Endpoints
@router.get(
    "/whatsapp/stats",
    response_model=WhatsAppStatsSummary,
    summary="Get WhatsApp Communication and Delivery Statistics",
)
async def get_whatsapp_stats(
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(verify_admin_auth),
) -> WhatsAppStatsSummary:
    """Returns WhatsApp message volume by status (pending, sent, delivered, read, failed)."""
    stats = await whatsapp_service.get_communication_stats(db=db)
    return WhatsAppStatsSummary(**stats)


@router.get(
    "/whatsapp/messages",
    response_model=WhatsAppMessageListResponse,
    summary="List, Search, and Filter WhatsApp Messages with Pagination",
)
async def list_whatsapp_messages(
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(verify_admin_auth),
    registration_id: Optional[str] = Query(None, description="Filter by registration ID"),
    phone_number: Optional[str] = Query(None, description="Filter by phone number"),
    message_type: Optional[str] = Query(None, description="Filter by message type"),
    status: Optional[str] = Query(None, description="Filter by delivery status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
) -> WhatsAppMessageListResponse:
    """List WhatsApp message logs with search and filtering."""
    res = await whatsapp_service.get_messages_list(
        db=db,
        registration_id=registration_id,
        phone_number=phone_number,
        message_type=message_type,
        status=status,
        page=page,
        page_size=page_size,
    )
    return WhatsAppMessageListResponse(**res)


@router.post(
    "/whatsapp/messages/{message_id}/retry",
    summary="Retry Individual Failed WhatsApp Message",
)
async def retry_whatsapp_message(
    message_id: str,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(verify_admin_auth),
) -> Dict[str, Any]:
    """Retry sending a specific failed WhatsApp message."""
    res = await whatsapp_service.retry_failed_message(db=db, message_id=message_id)
    if res.get("status") == "FAILED" and res.get("error") == "Message record not found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Message '{message_id}' not found.")
    return res


@router.post(
    "/whatsapp/retry-failed",
    response_model=WhatsAppRetryResponse,
    summary="Retry All Failed WhatsApp Messages",
)
async def retry_all_failed_whatsapp(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(verify_admin_auth),
) -> WhatsAppRetryResponse:
    """Batch retries all failed WhatsApp messages."""
    res = await whatsapp_service.retry_failed_messages(db=db, limit=limit)
    return WhatsAppRetryResponse(**res)


@router.get(
    "/leads",
    response_model=AdminLeadsResponse,
    summary="List, Search, and Filter Leads with Pagination",
)
async def list_admin_leads(
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(verify_admin_auth),
    search: Optional[str] = Query(None, description="Search by name, email, or phone"),
    status: Optional[str] = Query(None, description="Filter by lead status"),
    utm_source: Optional[str] = Query(None, description="Filter by UTM source"),
    utm_campaign: Optional[str] = Query(None, description="Filter by UTM campaign"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> AdminLeadsResponse:
    """List participant leads with filtering and search."""
    query = select(Participant).options(
        selectinload(Participant.registrations).selectinload(Registration.category),
        selectinload(Participant.registrations).selectinload(Registration.payments),
    )

    conditions = []
    if search:
        s = f"%{search.strip()}%"
        conditions.append(
            or_(
                Participant.full_name.ilike(s),
                Participant.email.ilike(s),
                Participant.phone_number.ilike(s),
            )
        )
    if status:
        conditions.append(Participant.lead_status == status.strip().upper())

    if conditions:
        query = query.where(and_(*conditions))

    # Count total matching
    count_query = select(func.count(Participant.id))
    if conditions:
        count_query = count_query.where(and_(*conditions))
    total = (await db.execute(count_query)).scalar_one() or 0

    # Paginated query
    query = query.order_by(Participant.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    records = (await db.execute(query)).scalars().all()

    items: List[AdminLeadItem] = []
    for p in records:
        latest_reg = p.registrations[-1] if p.registrations else None
        payment = latest_reg.payments[0] if (latest_reg and latest_reg.payments) else None
        
        # Apply UTM source/campaign filters if requested
        if utm_source and latest_reg and (latest_reg.utm_source or "").lower() != utm_source.strip().lower():
            continue
        if utm_campaign and latest_reg and (latest_reg.utm_campaign or "").lower() != utm_campaign.strip().lower():
            continue

        items.append(
            AdminLeadItem(
                id=p.id,
                name=p.full_name,
                email=p.email,
                phone=p.phone_number,
                city=p.city,
                state=p.state,
                category_code=latest_reg.category.code if (latest_reg and latest_reg.category) else None,
                category_title=latest_reg.category.title if (latest_reg and latest_reg.category) else None,
                lead_status=p.lead_status or "NEW",
                payment_status=payment.status if payment else "NONE",
                registration_status=latest_reg.status if latest_reg else "NONE",
                registration_code=latest_reg.registration_code if latest_reg else None,
                amount_inr=float(payment.amount_inr) if payment else (float(latest_reg.category.price_inr) if (latest_reg and latest_reg.category) else 0.0),
                utm_source=latest_reg.utm_source if latest_reg else None,
                utm_medium=latest_reg.utm_medium if latest_reg else None,
                utm_campaign=latest_reg.utm_campaign if latest_reg else None,
                zoho_sync_status=latest_reg.zoho_sync_status if latest_reg else "PENDING",
                zoho_lead_id=p.zoho_lead_id,
                created_at=p.created_at.isoformat() if p.created_at else "",
            )
        )

    return AdminLeadsResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=items,
    )


@router.patch(
    "/leads/{lead_id}/status",
    response_model=AdminLeadItem,
    summary="Update Lead Status (NEW, CONTACTED, REGISTERED, PAYMENT_PENDING, CONVERTED, LOST)",
)
async def update_lead_status(
    lead_id: str,
    payload: LeadStatusUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(verify_admin_auth),
) -> AdminLeadItem:
    """Update participant's lead status with status validation."""
    query = (
        select(Participant)
        .options(
            selectinload(Participant.registrations).selectinload(Registration.category),
            selectinload(Participant.registrations).selectinload(Registration.payments),
        )
        .where(Participant.id == lead_id)
    )
    res = await db.execute(query)
    participant = res.scalar_one_or_none()

    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lead/Participant with ID '{lead_id}' not found.",
        )

    participant.lead_status = payload.status
    await db.commit()
    await db.refresh(participant)

    latest_reg = participant.registrations[-1] if participant.registrations else None
    payment = latest_reg.payments[0] if (latest_reg and latest_reg.payments) else None

    return AdminLeadItem(
        id=participant.id,
        name=participant.full_name,
        email=participant.email,
        phone=participant.phone_number,
        city=participant.city,
        state=participant.state,
        category_code=latest_reg.category.code if (latest_reg and latest_reg.category) else None,
        category_title=latest_reg.category.title if (latest_reg and latest_reg.category) else None,
        lead_status=participant.lead_status,
        payment_status=payment.status if payment else "NONE",
        registration_status=latest_reg.status if latest_reg else "NONE",
        registration_code=latest_reg.registration_code if latest_reg else None,
        amount_inr=float(payment.amount_inr) if payment else (float(latest_reg.category.price_inr) if (latest_reg and latest_reg.category) else 0.0),
        utm_source=latest_reg.utm_source if latest_reg else None,
        utm_medium=latest_reg.utm_medium if latest_reg else None,
        utm_campaign=latest_reg.utm_campaign if latest_reg else None,
        zoho_sync_status=latest_reg.zoho_sync_status if latest_reg else "PENDING",
        zoho_lead_id=participant.zoho_lead_id,
        created_at=participant.created_at.isoformat() if participant.created_at else "",
    )


@router.get(
    "/registrations",
    response_model=AdminRegistrationsResponse,
    summary="List, Search, Filter, Sort, and Paginate Registrations",
)
async def list_admin_registrations(
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(verify_admin_auth),
    search: Optional[str] = Query(None, description="Search by registration code, BIB, name, email, or phone"),
    category: Optional[str] = Query(None, description="Filter by category code (5K, 10K, 21K)"),
    status: Optional[str] = Query(None, description="Filter by registration status (CONFIRMED, PENDING, CANCELLED)"),
    payment_status: Optional[str] = Query(None, description="Filter by payment status (SUCCESS, PENDING, FAILED)"),
    utm_source: Optional[str] = Query(None, description="Filter by UTM source"),
    utm_campaign: Optional[str] = Query(None, description="Filter by UTM campaign"),
    sort_by: str = Query("created_at", description="Field to sort by (created_at, registration_code, status)"),
    sort_order: str = Query("desc", description="Sort order (asc, desc)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> AdminRegistrationsResponse:
    """Comprehensive registration query endpoint with filtering, search, sorting, and pagination."""
    query = select(Registration).options(
        selectinload(Registration.participant),
        selectinload(Registration.category),
        selectinload(Registration.payments),
    )

    conditions = []
    if search:
        s = f"%{search.strip()}%"
        conditions.append(
            or_(
                Registration.registration_code.ilike(s),
                Registration.bib_number.ilike(s),
                Registration.participant.has(Participant.full_name.ilike(s)),
                Registration.participant.has(Participant.email.ilike(s)),
                Registration.participant.has(Participant.phone_number.ilike(s)),
            )
        )
    if category:
        conditions.append(Registration.category.has(RaceCategory.code == category.strip().upper()))
    if status:
        conditions.append(Registration.status == status.strip().upper())
    if utm_source:
        conditions.append(Registration.utm_source.ilike(utm_source.strip()))
    if utm_campaign:
        conditions.append(Registration.utm_campaign.ilike(utm_campaign.strip()))

    if conditions:
        query = query.where(and_(*conditions))

    # Total matching count
    count_query = select(func.count(Registration.id))
    if conditions:
        count_query = count_query.where(and_(*conditions))
    total = (await db.execute(count_query)).scalar_one() or 0

    # Sorting
    sort_col = Registration.created_at
    if sort_by == "registration_code":
        sort_col = Registration.registration_code
    elif sort_by == "status":
        sort_col = Registration.status

    if sort_order.lower() == "asc":
        query = query.order_by(asc(sort_col))
    else:
        query = query.order_by(desc(sort_col))

    # Pagination
    query = query.offset((page - 1) * page_size).limit(page_size)
    records = (await db.execute(query)).scalars().all()

    items: List[AdminRegistrationItem] = []
    for r in records:
        payment = r.payments[0] if r.payments else None
        
        # Filter payment status in memory if specified
        if payment_status and payment and payment.status != payment_status.strip().upper():
            continue

        items.append(
            AdminRegistrationItem(
                registration_id=r.id,
                registration_code=r.registration_code,
                bib_number=r.bib_number,
                status=r.status,
                category_code=r.category.code if r.category else "",
                category_title=r.category.title if r.category else "",
                participant_name=r.participant.full_name if r.participant else "Runner",
                email=r.participant.email if r.participant else "",
                phone=r.participant.phone_number if r.participant else "",
                city=r.participant.city if r.participant else "",
                amount_inr=float(payment.amount_inr) if payment else (float(r.category.price_inr) if r.category else 0.0),
                payment_status=payment.status if payment else "NONE",
                razorpay_payment_id=payment.razorpay_payment_id if payment else None,
                utm_source=r.utm_source,
                utm_medium=r.utm_medium,
                utm_campaign=r.utm_campaign,
                zoho_sync_status=r.zoho_sync_status or "PENDING",
                zoho_lead_id=r.participant.zoho_lead_id if r.participant else None,
                zoho_last_sync_attempt=r.zoho_last_sync_attempt.isoformat() if r.zoho_last_sync_attempt else None,
                created_at=r.created_at.isoformat() if r.created_at else "",
                confirmed_at=r.confirmed_at.isoformat() if r.confirmed_at else None,
            )
        )

    return AdminRegistrationsResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=items,
    )


@router.get(
    "/analytics",
    response_model=AdminAnalyticsResponse,
    summary="Marketing Funnel & Conversion Attribution Analytics",
)
async def get_admin_analytics(
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(verify_admin_auth),
) -> AdminAnalyticsResponse:
    """
    Computes real marketing and conversion analytics:
    - Funnel stages: Leads -> Registered -> Paid
    - Conversion rates: Lead to Reg %, Reg to Paid %, Overall %
    - Performance by category (5K, 10K, 21K)
    - Attribution by UTM Source (Instagram, Facebook, Google, Direct, Other)
    - Revenue metrics based only on verified payments
    """
    # 1. Funnel Calculations
    total_leads = (await db.execute(select(func.count(Participant.id)))).scalar_one() or 0
    total_reg = (await db.execute(select(func.count(Registration.id)))).scalar_one() or 0
    total_paid = (
        await db.execute(select(func.count(Registration.id)).where(Registration.status == "CONFIRMED"))
    ).scalar_one() or 0

    lead_to_reg = round((total_reg / total_leads) * 100, 2) if total_leads > 0 else 0.0
    reg_to_paid = round((total_paid / total_reg) * 100, 2) if total_reg > 0 else 0.0
    overall_conv = round((total_paid / total_leads) * 100, 2) if total_leads > 0 else 0.0

    funnel = FunnelMetrics(
        total_leads=total_leads,
        total_registered=total_reg,
        total_paid=total_paid,
        lead_to_reg_rate_pct=lead_to_reg,
        reg_to_paid_rate_pct=reg_to_paid,
        overall_conversion_rate_pct=overall_conv,
    )

    # 2. Revenue Summary
    revenue_res = await db.execute(
        select(
            func.coalesce(func.sum(Payment.amount_inr), 0.0),
            func.count(Payment.id),
        ).where(Payment.status == "SUCCESS")
    )
    total_rev, paid_count = revenue_res.one()
    total_rev = float(total_rev or 0.0)
    paid_count = int(paid_count or 0)
    aov = round(total_rev / paid_count, 2) if paid_count > 0 else 0.0

    revenue_metrics = RevenueMetrics(
        total_revenue_inr=total_rev,
        paid_participants_count=paid_count,
        average_order_value_inr=aov,
    )

    # 3. Category Breakdown
    categories = (await db.execute(select(RaceCategory).order_by(RaceCategory.distance_km.asc()))).scalars().all()
    cat_analytics: List[CategoryAnalytics] = []
    for c in categories:
        cat_reg_count = (
            await db.execute(select(func.count(Registration.id)).where(Registration.category_id == c.id))
        ).scalar_one() or 0
        cat_paid_count = (
            await db.execute(
                select(func.count(Registration.id)).where(
                    and_(Registration.category_id == c.id, Registration.status == "CONFIRMED")
                )
            )
        ).scalar_one() or 0
        cat_rev = float(cat_paid_count * float(c.price_inr))
        share = round((cat_paid_count / paid_count) * 100, 1) if paid_count > 0 else 0.0

        cat_analytics.append(
            CategoryAnalytics(
                category_code=c.code,
                category_title=c.title,
                registered_count=cat_reg_count,
                paid_count=cat_paid_count,
                revenue_inr=cat_rev,
                share_pct=share,
            )
        )

    # 4. UTM Source Analytics
    utm_query = select(
        Registration.utm_source,
        func.count(Registration.id),
        func.count(func.nullif(Registration.status != "CONFIRMED", True)),
    ).group_by(Registration.utm_source)
    
    utm_res = await db.execute(utm_query)
    utm_list: List[UtmSourceAnalytics] = []
    
    for src, count_total, count_paid in utm_res.all():
        source_name = (src or "direct").lower()
        c_tot = int(count_total or 0)
        c_paid = int(count_paid or 0)
        c_rate = round((c_paid / c_tot) * 100, 2) if c_tot > 0 else 0.0
        
        # Calculate revenue for this source
        src_rev_query = (
            select(func.coalesce(func.sum(Payment.amount_inr), 0.0))
            .select_from(Registration)
            .join(Payment, Payment.registration_id == Registration.id)
            .where(
                and_(
                    Payment.status == "SUCCESS",
                    Registration.utm_source == src if src else Registration.utm_source.is_(None),
                )
            )
        )
        src_rev = float((await db.execute(src_rev_query)).scalar_one() or 0.0)

        utm_list.append(
            UtmSourceAnalytics(
                source=source_name,
                leads_count=c_tot,
                registered_count=c_tot,
                paid_count=c_paid,
                conversion_rate_pct=c_rate,
                revenue_inr=src_rev,
            )
        )

    # Sort UTM sources by revenue descending
    utm_list.sort(key=lambda x: x.revenue_inr, reverse=True)

    return AdminAnalyticsResponse(
        funnel=funnel,
        categories=cat_analytics,
        utm_sources=utm_list,
        revenue=revenue_metrics,
    )


@router.get(
    "/export/leads",
    summary="Export Leads as CSV File",
)
async def export_leads_csv(
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(verify_admin_auth),
) -> StreamingResponse:
    """Generates and streams downloadable CSV for all participant leads."""
    query = select(Participant).options(
        selectinload(Participant.registrations).selectinload(Registration.category),
        selectinload(Participant.registrations).selectinload(Registration.payments),
    ).order_by(Participant.created_at.desc())

    records = (await db.execute(query)).scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Lead ID",
        "Full Name",
        "Email",
        "Phone Number",
        "City",
        "State",
        "Race Category",
        "Lead Status",
        "Registration Status",
        "Payment Status",
        "Registration Code",
        "Amount (INR)",
        "UTM Source",
        "UTM Medium",
        "UTM Campaign",
        "Zoho Sync Status",
        "Zoho Lead ID",
        "Created Date",
    ])

    for p in records:
        latest_reg = p.registrations[-1] if p.registrations else None
        payment = latest_reg.payments[0] if (latest_reg and latest_reg.payments) else None
        writer.writerow([
            p.id,
            p.full_name,
            p.email,
            p.phone_number,
            p.city,
            p.state,
            latest_reg.category.title if (latest_reg and latest_reg.category) else "",
            p.lead_status or "NEW",
            latest_reg.status if latest_reg else "NONE",
            payment.status if payment else "NONE",
            latest_reg.registration_code if latest_reg else "",
            float(payment.amount_inr) if payment else (float(latest_reg.category.price_inr) if (latest_reg and latest_reg.category) else 0.0),
            latest_reg.utm_source if latest_reg else "",
            latest_reg.utm_medium if latest_reg else "",
            latest_reg.utm_campaign if latest_reg else "",
            latest_reg.zoho_sync_status if latest_reg else "PENDING",
            p.zoho_lead_id or "",
            p.created_at.strftime("%Y-%m-%d %H:%M:%S") if p.created_at else "",
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="marathon_leads.csv"'},
    )


@router.get(
    "/export/registrations",
    summary="Export Registrations as CSV File",
)
async def export_registrations_csv(
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(verify_admin_auth),
) -> StreamingResponse:
    """Generates and streams downloadable CSV for all registrations."""
    query = select(Registration).options(
        selectinload(Registration.participant),
        selectinload(Registration.category),
        selectinload(Registration.payments),
    ).order_by(Registration.created_at.desc())

    records = (await db.execute(query)).scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Registration ID",
        "Registration Code",
        "BIB Number",
        "Status",
        "Category",
        "Distance (KM)",
        "Participant Name",
        "Email",
        "Phone Number",
        "City",
        "State",
        "Amount (INR)",
        "Payment Status",
        "Razorpay Payment ID",
        "UTM Source",
        "UTM Medium",
        "UTM Campaign",
        "Zoho Sync Status",
        "Created At",
        "Confirmed At",
    ])

    for r in records:
        payment = r.payments[0] if r.payments else None
        writer.writerow([
            r.id,
            r.registration_code,
            r.bib_number or "",
            r.status,
            r.category.title if r.category else "",
            r.category.distance_km if r.category else "",
            r.participant.full_name if r.participant else "",
            r.participant.email if r.participant else "",
            r.participant.phone_number if r.participant else "",
            r.participant.city if r.participant else "",
            r.participant.state if r.participant else "",
            float(payment.amount_inr) if payment else (float(r.category.price_inr) if r.category else 0.0),
            payment.status if payment else "NONE",
            payment.razorpay_payment_id if payment else "",
            r.utm_source or "",
            r.utm_medium or "",
            r.utm_campaign or "",
            r.zoho_sync_status or "PENDING",
            r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else "",
            r.confirmed_at.strftime("%Y-%m-%d %H:%M:%S") if r.confirmed_at else "",
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="marathon_registrations.csv"'},
    )


@router.post(
    "/demo-reset",
    summary="Reset demo registrations and logs (Allowed only in DEBUG/Mock Mode)",
)
async def reset_demo_data(
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(verify_admin_auth),
) -> Dict[str, Any]:
    """
    Safely reset demo registrations, payments, participants, and integration logs.
    Strictly blocked in production environments.
    """
    if not (settings.DEBUG or settings.INTEGRATIONS_MOCK_MODE):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo data reset is strictly prohibited in production environments.",
        )

    # 1. Delete transient demo logs, payments, registrations, and participants
    await db.execute(delete(IntegrationLog))
    await db.execute(delete(Payment))
    await db.execute(delete(Registration))
    await db.execute(delete(Participant))

    # 2. Reset category counts to 0
    cat_query = select(RaceCategory)
    cats = (await db.execute(cat_query)).scalars().all()
    for c in cats:
        c.current_count = 0

    await db.commit()
    logger.info("Demo database state reset successfully.")

    return {
        "status": "success",
        "message": "Demo data reset successfully. Race categories and slot counters restored to baseline.",
    }
