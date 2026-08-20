import uuid
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class WhatsAppMessage(Base):
    __tablename__ = "whatsapp_messages"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    registration_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("registrations.id", ondelete="CASCADE"), nullable=True, index=True
    )
    participant_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("participants.id", ondelete="CASCADE"), nullable=True, index=True
    )
    phone_number: Mapped[str] = mapped_column(String(30), index=True, nullable=False)
    
    # Message / Workflow Type (e.g. REGISTRATION_CONFIRMATION, PAYMENT_CONFIRMATION, REMINDER_7_DAYS, REMINDER_3_DAYS, REMINDER_1_DAY, REMINDER_RACE_DAY, POST_EVENT_THANKS)
    message_type: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    template_name: Mapped[str] = mapped_column(String(100), nullable=False)
    message_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Provider details (MOCK, WHATSAPP_CLOUD_API)
    provider: Mapped[str] = mapped_column(String(30), default="MOCK", nullable=False)
    provider_message_id: Mapped[Optional[str]] = mapped_column(String(150), index=True, nullable=True)
    
    # Idempotency Key (e.g. "reg_id:msg_type")
    idempotency_key: Mapped[str] = mapped_column(String(150), unique=True, index=True, nullable=False)
    
    # Delivery Status (PENDING, SENT, DELIVERED, READ, FAILED)
    status: Mapped[str] = mapped_column(String(20), default="PENDING", index=True, nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    error_message: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    registration = relationship("Registration", backref="whatsapp_messages")
    participant = relationship("Participant", backref="whatsapp_messages")

    def __repr__(self) -> str:
        return f"<WhatsAppMessage {self.id} | {self.message_type} -> {self.phone_number} [{self.status}]>"
