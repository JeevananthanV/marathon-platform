import uuid
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, ForeignKey, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Registration(Base):
    __tablename__ = "registrations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    registration_code: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False
    ) # e.g. "MX26-000001"
    participant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("participants.id", ondelete="CASCADE"), nullable=False
    )
    category_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("race_categories.id", ondelete="RESTRICT"), nullable=False
    )
    bib_number: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default="PENDING", index=True, nullable=False
    ) # PENDING, CONFIRMED, CANCELLED, REFUNDED

    # UTM and Marketing Attribution
    utm_source: Mapped[str] = mapped_column(String(100), nullable=True) # instagram, facebook, etc.
    utm_medium: Mapped[str] = mapped_column(String(100), nullable=True) # cpc, story, reel, banner
    utm_campaign: Mapped[str] = mapped_column(String(100), nullable=True)
    utm_term: Mapped[str] = mapped_column(String(100), nullable=True)
    utm_content: Mapped[str] = mapped_column(String(100), nullable=True)
    referrer: Mapped[str] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[str] = mapped_column(String(50), nullable=True)
    user_agent: Mapped[str] = mapped_column(String(255), nullable=True)

    # Consent and Policy
    terms_accepted: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    communication_consent: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Zoho CRM Synchronization Status (Phase 5)
    zoho_sync_status: Mapped[str] = mapped_column(
        String(20), default="PENDING", index=True, nullable=False
    ) # PENDING, SYNCED, FAILED
    zoho_last_sync_attempt: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    zoho_last_successful_sync: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    zoho_error_message: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    zoho_retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    confirmed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    participant = relationship("Participant", back_populates="registrations")
    category = relationship("RaceCategory", back_populates="registrations")
    payments = relationship("Payment", back_populates="registration", cascade="all, delete-orphan")
    integration_logs = relationship("IntegrationLog", back_populates="registration", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Registration {self.registration_code} - Status: {self.status} (Zoho: {self.zoho_sync_status})>"
