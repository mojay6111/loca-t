"""USSD menu logic.

Africa's Talking sends the full chain of answers in `text`, joined by '*'
(for example "2*Bibi Homestay*2"). We read that chain on every request, so no
per-step state needs saving. Replies start with "CON " (continue) or "END ".
"""
from sqlalchemy.orm import Session

from locat.i18n import t
from locat.services.booking_service import (
    get_or_create_user,
    get_user,
    register_property,
)

# Shared later with the forecasting layer, so keep the spelling consistent.
DESTINATIONS = ["Maasai Mara", "Naivasha", "Diani", "Lamu", "Amboseli"]


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


def handle_ussd(db: Session, phone: str, text: str) -> str:
    steps = text.split("*") if text else []
    user = get_user(db, phone)
    lang = user.language if user else "en"

    if not steps:
        return _con(t(lang, "main_menu"))

    choice, rest = steps[0], steps[1:]

    if choice in ("1", "3"):  # Find a stay / My bookings: built in Phase 4b
        return _end(t(lang, "coming_soon"))
    if choice == "2":
        return _host_registration(db, phone, lang, rest)
    if choice == "4":
        return _language(db, phone, lang, rest)
    return _end(t(lang, "invalid"))


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