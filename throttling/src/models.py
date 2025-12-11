"""SQLAlchemy models for throttling service"""

from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Boolean, Float, Integer
from datetime import datetime


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for SQLAlchemy models"""

    pass


class Domain(Base):
    """Domain configuration model"""

    __tablename__ = "domain"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Token bucket rate limiting configuration
    requests_per_second: Mapped[float] = mapped_column(Float, default=1.0)
    burst_capacity: Mapped[int] = mapped_column(Integer, default=2)
    concurrent_requests: Mapped[int] = mapped_column(Integer, default=1)

    # Retry configuration
    max_retries: Mapped[int] = mapped_column(Integer, default=3)
    retry_delay: Mapped[float] = mapped_column(Float, default=5.0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self):
        return f"<Domain(name='{self.name}', rps={self.requests_per_second})>"
