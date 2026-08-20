import uuid
from datetime import datetime, timezone
from sqlalchemy import String, ForeignKey, Numeric, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    registration_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("registrations.id", ondelete="CASCADE"), nullable=False
    )
    razorpay_order_id: Mapped[str] = mapped_column(
        String(100), unique=True, index=True, nullable=False
    )
    razorpay_payment_id: Mapped[str] = mapped_column(
        String(100), unique=True, index=True, nullable=True
    )
    razorpay_signature: Mapped[str] = mapped_column(String(255), nullable=True)
    amount_inr: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="INR", nullable=False)
    status: Mapped[str] = mapped_column(
        String(30), default="PENDING", index=True, nullable=False
    ) # PENDING, SUCCESS, FAILED, CANCELLED
    error_code: Mapped[str] = mapped_column(String(100), nullable=True)
    error_description: Mapped[str] = mapped_column(String(255), nullable=True)
    raw_webhook_payload: Mapped[str] = mapped_column(Text, nullable=True)
    
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    registration = relationship("Registration", back_populates="payments")

    def __repr__(self) -> str:
        return f"<Payment {self.razorpay_order_id} - {self.status} (INR {self.amount_inr})>"
