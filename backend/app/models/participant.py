import uuid
from datetime import datetime, timezone, date
from sqlalchemy import String, Date, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Participant(Base):
    __tablename__ = "participants"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    phone_number: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    gender: Mapped[str] = mapped_column(String(20), nullable=False) # MALE, FEMALE, OTHER
    blood_group: Mapped[str] = mapped_column(String(10), nullable=False) # A+, B+, O+, AB+, etc.
    tshirt_size: Mapped[str] = mapped_column(String(10), nullable=False) # XS, S, M, L, XL, XXL
    emergency_contact_name: Mapped[str] = mapped_column(String(150), nullable=False)
    emergency_contact_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Lead & Marketing Funnel Status (NEW, CONTACTED, REGISTERED, PAYMENT_PENDING, CONVERTED, LOST)
    lead_status: Mapped[str] = mapped_column(
        String(30), default="NEW", index=True, nullable=False
    )

    # WhatsApp & Communication Consent
    whatsapp_consent: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Zoho CRM Record ID Reference
    zoho_lead_id: Mapped[str] = mapped_column(String(100), nullable=True, index=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    registrations = relationship("Registration", back_populates="participant", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Participant {self.full_name} ({self.email}) - Lead: {self.lead_status}>"
