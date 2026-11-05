"""Users, properties and bookings."""
import secrets
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from locat.db.models import Booking, Property, User

DEPOSIT_RATE = 0.30   # share of the total taken as deposit
HOLD_MINUTES = 15     # how long an unpaid (pending) booking holds its rooms

# No 0/O/1/I so codes are easy to read out over a phone call.
_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def get_user(db: Session, phone: str) -> User | None:
    return db.scalar(select(User).where(User.phone == phone))


def get_or_create_user(db: Session, phone: str, role: str = "traveler") -> User:
    user = get_user(db, phone)
    if user is None:
        user = User(phone=phone, role=role)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def generate_listing_code(db: Session) -> str:
    while True:
        code = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(6))
        exists = db.scalar(select(Property.id).where(Property.listing_code == code))
        if exists is None:
            return code


def register_property(
    db: Session,
    phone: str,
    name: str,
    destination: str,
    rooms: int,
    base_price: float,
) -> Property:
    """Create the host (if new) and their first/next property."""
    user = get_or_create_user(db, phone, role="host")
    if user.role != "host":
        user.role = "host"
        db.commit()

    prop = Property(
        host_id=user.id,
        name=name,
        destination=destination,
        rooms=rooms,
        base_price=base_price,
        listing_code=generate_listing_code(db),
    )
    db.add(prop)
    db.commit()
    db.refresh(prop)
    return prop


def list_properties(db: Session, destination: str, limit: int = 5) -> list[Property]:
    stmt = (
        select(Property)
        .where(Property.destination == destination, Property.is_active.is_(True))
        .order_by(Property.id)
        .limit(limit)
    )
    return list(db.scalars(stmt))


def booking_ref(booking: Booking) -> str:
    return f"LT{booking.id:04d}"


def quote(prop: Property, nights: int) -> tuple[float, float]:
    """Return (total, deposit) in KES."""
    total = prop.base_price * nights
    return total, float(round(total * DEPOSIT_RATE))


def rooms_taken(db: Session, property_id: int, check_in: date, check_out: date) -> int:
    """Rooms already committed for an overlapping stay."""
    hold_cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(
        minutes=HOLD_MINUTES
    )
    stmt = select(func.count(Booking.id)).where(
        Booking.property_id == property_id,
        Booking.check_in < check_out,
        Booking.check_out > check_in,
        or_(
            Booking.status.in_(["confirmed", "completed"]),
            and_(Booking.status == "pending", Booking.created_at >= hold_cutoff),
        ),
    )
    return db.scalar(stmt) or 0


def create_booking(
    db: Session,
    guest_phone: str,
    prop: Property,
    check_in: date,
    nights: int,
    guests: int,
) -> Booking:
    guest = get_or_create_user(db, guest_phone)
    total, deposit = quote(prop, nights)
    booking = Booking(
        property_id=prop.id,
        guest_id=guest.id,
        check_in=check_in,
        check_out=check_in + timedelta(days=nights),
        guests=guests,
        total_amount=total,
        deposit_amount=deposit,
        status="pending",
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


def recent_bookings_for_user(db: Session, user: User, limit: int = 3) -> list[Booking]:
    """Hosts see bookings on their places; travelers see their own."""
    if user.role == "host":
        stmt = (
            select(Booking)
            .join(Property, Booking.property_id == Property.id)
            .where(Property.host_id == user.id)
        )
    else:
        stmt = select(Booking).where(Booking.guest_id == user.id)
    return list(db.scalars(stmt.order_by(Booking.id.desc()).limit(limit)))