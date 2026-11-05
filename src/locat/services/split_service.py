"""Splitting a booking's money between host, guide and the community fund."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from locat.config import get_settings
from locat.db.models import Booking, RevenueSplit


def compute_split(
    total: float,
    community_rate: float | None = None,
    guide_rate: float = 0.0,
) -> dict[str, float]:
    """Community fund and guide take their share; the host keeps the rest."""
    if community_rate is None:
        community_rate = get_settings().community_fund_rate
    community = float(round(total * community_rate))
    guide = float(round(total * guide_rate))
    return {
        "host_amount": total - community - guide,
        "guide_amount": guide,
        "community_amount": community,
    }


def record_split(db: Session, booking: Booking) -> RevenueSplit:
    """Create the split row for a booking once (safe to call again)."""
    existing = db.scalar(
        select(RevenueSplit).where(RevenueSplit.booking_id == booking.id)
    )
    if existing is not None:
        return existing

    split = RevenueSplit(booking_id=booking.id, **compute_split(booking.total_amount))
    db.add(split)
    db.commit()
    db.refresh(split)
    return split