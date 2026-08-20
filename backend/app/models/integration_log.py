import uuid
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import String, ForeignKey, Integer, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class IntegrationLog(Base):
    __tablename__ = "integration_logs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    registration_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("registrations.id", ondelete="CASCADE"), nullable=True
    )
    service_name: Mapped[str] = mapped_column(
        String(50), index=True, nullable=False
    )  # ZOHO_CRM, WHATSAPP, N8N, META_CAPI
    event_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # META_PURCHASE, META_LEAD, etc.
    status: Mapped[str] = mapped_column(
        String(20), default="SUCCESS", index=True, nullable=False
    )  # SUCCESS, FAILED, RETRYING
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    request_payload: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    response_payload: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    registration = relationship("Registration", back_populates="integration_logs")

    def __repr__(self) -> str:
        return f"<IntegrationLog {self.service_name} - {self.event_type} ({self.status})>"
