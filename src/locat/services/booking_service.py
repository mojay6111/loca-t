"""Users, properties and (later) bookings."""
import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from locat.db.models import Property, User

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