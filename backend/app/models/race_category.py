import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Numeric, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class RaceCategory(Base):
    __tablename__ = "race_categories"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    title: Mapped[str] = mapped_column(String(100), nullable=False) # e.g. "21K Half Marathon"
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False) # e.g. "21K"
    distance_km: Mapped[float] = mapped_column(Numeric(4, 1), nullable=False)
    price_inr: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    max_capacity: Mapped[int] = mapped_column(Integer, default=500, nullable=False)
    current_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    bib_prefix: Mapped[str] = mapped_column(String(10), default="RUN", nullable=False)
    min_age: Mapped[int] = mapped_column(Integer, default=14, nullable=False)
    start_time: Mapped[str] = mapped_column(String(50), default="05:30 AM", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    registrations = relationship("Registration", back_populates="category", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<RaceCategory {self.code} - {self.title}>"
