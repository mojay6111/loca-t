"""All Loca-T database tables."""
from datetime import date, datetime

from sqlalchemy import (
    Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from locat.db.session import Base


class User(Base):
    """Hosts, guides and travelers, keyed by phone number."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    role: Mapped[str] = mapped_column(String(20), default="traveler")  # host | guide | traveler
    language: Mapped[str] = mapped_column(String(5), default="en")     # en | sw
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Property(Base):
    """A homestay, lodge or tour listing."""
    __tablename__ = "properties"

    id: Mapped[int] = mapped_column(primary_key=True)
    host_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    destination: Mapped[str] = mapped_column(String(80), index=True)
    property_type: Mapped[str] = mapped_column(String(30), default="homestay")
    rooms: Mapped[int] = mapped_column(Integer, default=1)
    base_price: Mapped[float] = mapped_column(Float)  # KES per night
    listing_code: Mapped[str] = mapped_column(String(10), unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    host: Mapped["User"] = relationship("User")


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), index=True)
    guest_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    check_in: Mapped[date] = mapped_column(Date)
    check_out: Mapped[date] = mapped_column(Date)
    guests: Mapped[int] = mapped_column(Integer, default=1)
    total_amount: Mapped[float] = mapped_column(Float)
    deposit_amount: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending | confirmed | cancelled | completed
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    property: Mapped["Property"] = relationship("Property")
    guest: Mapped["User"] = relationship("User")


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id"), index=True)
    phone: Mapped[str] = mapped_column(String(20))
    amount: Mapped[float] = mapped_column(Float)
    provider_ref: Mapped[str | None] = mapped_column(String(80), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending | success | failed
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class RevenueSplit(Base):
    """How one booking's money is shared: host, guide, community fund."""
    __tablename__ = "revenue_splits"

    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id"), unique=True)
    host_amount: Mapped[float] = mapped_column(Float)
    guide_amount: Mapped[float] = mapped_column(Float, default=0.0)
    community_amount: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class DemandHistory(Base):
    """Demand observations used to train the forecaster."""
    __tablename__ = "demand_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    obs_date: Mapped[date] = mapped_column(Date, index=True)
    destination: Mapped[str] = mapped_column(String(80), index=True)
    demand: Mapped[float] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(20), default="synthetic")  # real | synthetic | live


class PriceAdvice(Base):
    __tablename__ = "price_advice"

    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), index=True)
    week_start: Mapped[date] = mapped_column(Date)
    current_price: Mapped[float] = mapped_column(Float)
    suggested_price: Mapped[float] = mapped_column(Float)
    reason: Mapped[str] = mapped_column(Text, default="")
    accepted: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class UssdSession(Base):
    """Tracks where each caller is in the USSD menu."""
    __tablename__ = "ussd_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    phone: Mapped[str] = mapped_column(String(20))
    step: Mapped[str] = mapped_column(String(40), default="start")
    data: Mapped[str] = mapped_column(Text, default="{}")  # JSON blob of answers so far
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )