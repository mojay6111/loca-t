"""USSD menu logic.

Africa's Talking sends the full chain of answers in `text`, joined by '*'
(for example "1*2*1"). We read that chain on every request, so no per-step
state needs saving. Replies start with "CON " (continue) or "END ".
"""
import logging
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from locat.db.models import Property, User
from locat.i18n import t
from locat.services.booking_service import (
    booking_ref,
    create_booking,
    get_or_create_user,
    get_user,
    list_properties,
    quote,
    recent_bookings_for_user,
    register_property,
    rooms_taken,
)
from locat.services.payments_service import PaymentStartError, initiate_deposit
from locat.services.advice_service import advice_for_property, render_outlook

# Shared later with the forecasting layer, so keep the spelling consistent.
DESTINATIONS = ["Maasai Mara", "Naivasha", "Diani", "Lamu", "Amboseli"]


# ---------- small helpers ----------

def _con(message: str) -> str:
    return f"CON {message}"


def _end(message: str) -> str:
    return f"END {message}"


def _parse_int(raw: str, low: int, high: int) -> int | None:
    raw = raw.strip()
    if not raw.isdigit():
        return None
    value = int(raw)
    return value if low <= value <= high else None


def _destination_options() -> str:
    return "\n".join(f"{i}. {d}" for i, d in enumerate(DESTINATIONS, start=1))


def _fmt(d: date) -> str:
    return d.strftime("%a %d %b")  # e.g. "Fri 27 Nov"


def _upcoming_fridays() -> tuple[date, date]:
    today = date.today()
    first = today + timedelta(days=(4 - today.weekday()) % 7)
    return first, first + timedelta(days=7)


def _parse_ddmm(raw: str) -> date | None:
    """'2811' -> the next 28 November (this year, or next if already past)."""
    raw = raw.strip()
    if len(raw) != 4 or not raw.isdigit():
        return None
    day, month = int(raw[:2]), int(raw[2:])
    today = date.today()
    for year in (today.year, today.year + 1):
        try:
            candidate = date(year, month, day)
        except ValueError:
            continue
        if candidate >= today:
            return candidate
    return None


# ---------- entry point ----------

def handle_ussd(db: Session, phone: str, text: str) -> str:
    steps = text.split("*") if text else []
    user = get_user(db, phone)
    lang = user.language if user else "en"

    if not steps:
        return _con(t(lang, "main_menu"))

    choice, rest = steps[0], steps[1:]

    if choice == "1":
        return _find_stay(db, phone, lang, rest)
    if choice == "2":
        return _host_registration(db, phone, lang, rest)
    if choice == "3":
        return _my_bookings(db, user, lang)
    if choice == "4":
        return _language(db, phone, lang, rest)
    if choice == "5":
        return _outlook(db, user, lang)
    return _end(t(lang, "invalid"))


# ---------- 1. Find a stay (traveler) ----------

def _find_stay(db: Session, phone: str, lang: str, args: list[str]) -> str:
    n = len(args)

    if n == 0:
        return _con(t(lang, "find_destination", options=_destination_options()))

    dest_index = _parse_int(args[0], 1, len(DESTINATIONS))
    if dest_index is None:
        return _end(t(lang, "invalid"))
    stays = list_properties(db, DESTINATIONS[dest_index - 1])
    if not stays:
        return _end(t(lang, "no_listings"))

    if n == 1:
        options = "\n".join(
            f"{i}. {p.name[:22]} KES {p.base_price:.0f}"
            for i, p in enumerate(stays, start=1)
        )
        return _con(t(lang, "pick_stay", options=options))

    stay_index = _parse_int(args[1], 1, len(stays))
    if stay_index is None:
        return _end(t(lang, "invalid"))
    prop = stays[stay_index - 1]

    friday1, friday2 = _upcoming_fridays()
    if n == 2:
        return _con(t(lang, "ask_checkin", d1=_fmt(friday1), d2=_fmt(friday2)))

    # --- check-in date (options 1 and 2 use one step, option 3 uses two) ---
    date_choice = args[2]
    if date_choice == "1":
        check_in, used = friday1, 3
    elif date_choice == "2":
        check_in, used = friday2, 3
    elif date_choice == "3":
        if n == 3:
            return _con(t(lang, "ask_date"))
        check_in = _parse_ddmm(args[3])
        if check_in is None:
            return _end(t(lang, "invalid"))
        used = 4
    else:
        return _end(t(lang, "invalid"))

    rest = args[used:]
    m = len(rest)

    if m == 0:
        return _con(t(lang, "ask_nights"))
    nights = _parse_int(rest[0], 1, 14)
    if nights is None:
        return _end(t(lang, "invalid"))

    if m == 1:
        return _con(t(lang, "ask_guests"))
    guests = _parse_int(rest[1], 1, 20)
    if guests is None:
        return _end(t(lang, "invalid"))

    check_out = check_in + timedelta(days=nights)
    if rooms_taken(db, prop.id, check_in, check_out) >= prop.rooms:
        return _end(t(lang, "no_rooms"))

    total, deposit = quote(prop, nights)
    if m == 2:
        return _con(
            t(lang, "confirm_booking", name=prop.name[:30], check_in=_fmt(check_in),
              nights=nights, guests=guests, total=f"{total:.0f}",
              deposit=f"{deposit:.0f}")
        )

    if m == 3 and rest[2] == "1":
        booking = create_booking(db, phone, prop, check_in, nights, guests)
        try:
            initiate_deposit(db, booking)
        except PaymentStartError:
            return _end(t(lang, "payment_not_started"))
        return _end(
            t(lang, "booking_saved", ref=booking_ref(booking),
              deposit=f"{booking.deposit_amount:.0f}")
        )
    if m == 3 and rest[2] == "2":
        return _end(t(lang, "cancelled"))
    return _end(t(lang, "invalid"))


# ---------- 2. List my place (host) ----------

def _host_registration(db: Session, phone: str, lang: str, args: list[str]) -> str:
    n = len(args)

    if n == 0:
        return _con(t(lang, "ask_property_name"))

    name = args[0].strip()
    if not 2 <= len(name) <= 60:
        return _end(t(lang, "invalid"))
    if n == 1:
        return _con(t(lang, "ask_destination", options=_destination_options()))

    dest_index = _parse_int(args[1], 1, len(DESTINATIONS))
    if dest_index is None:
        return _end(t(lang, "invalid"))
    destination = DESTINATIONS[dest_index - 1]
    if n == 2:
        return _con(t(lang, "ask_rooms"))

    rooms = _parse_int(args[2], 1, 50)
    if rooms is None:
        return _end(t(lang, "invalid"))
    if n == 3:
        return _con(t(lang, "ask_price"))

    price = _parse_int(args[3], 100, 100000)
    if price is None:
        return _end(t(lang, "invalid"))
    if n == 4:
        return _con(
            t(lang, "confirm_listing", name=name, destination=destination,
              rooms=rooms, price=price)
        )

    if n == 5 and args[4] == "1":
        prop = register_property(db, phone, name, destination, rooms, price)
        return _end(t(lang, "listing_saved", code=prop.listing_code))
    if n == 5 and args[4] == "2":
        return _end(t(lang, "cancelled"))
    return _end(t(lang, "invalid"))


# ---------- 3. My bookings ----------

def _my_bookings(db: Session, user: User | None, lang: str) -> str:
    if user is None:
        return _end(t(lang, "no_bookings"))
    bookings = recent_bookings_for_user(db, user)
    if not bookings:
        return _end(t(lang, "no_bookings"))
    lines = "\n".join(
        f"{booking_ref(b)} {b.property.name[:12]} {_fmt(b.check_in)} "
        f"{t(lang, 'status_' + b.status)}"
        for b in bookings
    )
    return _end(t(lang, "my_bookings", lines=lines))


# ---------- 4. Language ----------

def _language(db: Session, phone: str, lang: str, args: list[str]) -> str:
    if not args:
        return _con(t(lang, "language_menu"))

    new_lang = {"1": "en", "2": "sw"}.get(args[0])
    if new_lang is None:
        return _end(t(lang, "invalid"))

    user = get_or_create_user(db, phone)
    user.language = new_lang
    db.commit()
    return _end(t(new_lang, "language_saved"))

# ---------- 5. My outlook (host) ----------

def _outlook(db: Session, user: User | None, lang: str) -> str:
    """The host's busiest nights, peak and price tip on one screen."""
    if user is None or user.role != "host":
        return _end(t(lang, "outlook_no_property"))
    prop = db.scalar(
        select(Property).where(Property.host_id == user.id).order_by(Property.id.desc())
    )
    if prop is None:
        return _end(t(lang, "outlook_no_property"))
    try:
        advice = advice_for_property(prop, days=60)
        return _end(render_outlook(advice, prop.name, lang, "ussd"))
    except Exception:  # the menu must always answer
        logger.exception("outlook failed for %s", prop.listing_code)
        return _end(t(lang, "outlook_unavailable"))