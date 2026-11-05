"""Kiswahili USSD/SMS strings. Keep each USSD screen under ~180 characters."""

STRINGS = {
    "main_menu": (
        "Karibu Loca-T\n"
        "1. Tafuta makazi\n"
        "2. Orodhesha mahali pangu\n"
        "3. Nafasi zangu\n"
        "4. Lugha/Language"
    ),
    "coming_soon": "Huduma hii inakuja hivi karibuni.",
    "invalid": "Ingizo si sahihi. Tafadhali piga tena.",
    "cancelled": "Imeghairiwa. Piga tena wakati wowote.",
    "ask_property_name": "Jina la mahali pako:",
    "ask_destination": "Mahali ni wapi?\n{options}",
    "ask_rooms": "Una vyumba vingapi?",
    "ask_price": "Bei kwa usiku (KES):",
    "confirm_listing": (
        "Thibitisha:\n{name}, {destination}\n"
        "Vyumba {rooms} @ KES {price}\n"
        "1. Thibitisha\n2. Ghairi"
    ),
    "listing_saved": "Uko hewani! Namba yako: {code}",
    "language_menu": "Chagua lugha:\n1. English\n2. Kiswahili",
    "language_saved": "Lugha imewekwa: Kiswahili.",
    "find_destination": "Unaenda wapi?\n{options}",
    "pick_stay": "Chagua makazi:\n{options}",
    "no_listings": "Hakuna makazi huko bado. Jaribu mahali pengine.",
    "ask_checkin": "Tarehe ya kuingia:\n1. {d1}\n2. {d2}\n3. Tarehe nyingine",
    "ask_date": "Andika tarehe kama DDMM (mf. 2811):",
    "ask_nights": "Usiku ngapi?",
    "ask_guests": "Wageni wangapi?",
    "no_rooms": "Samahani, hakuna vyumba tupu tarehe hizo.",
    "confirm_booking": (
        "{name}\n{check_in}, usiku {nights}, wageni {guests}\n"
        "Jumla KES {total}\nAmana KES {deposit}\n"
        "1. Thibitisha\n2. Ghairi"
    ),
    "booking_saved": "Imehifadhiwa! Namba {ref}. Amana KES {deposit}. Maelezo ya malipo kwa SMS hivi karibuni.",
    "my_bookings": "Nafasi zako:\n{lines}",
    "no_bookings": "Huna nafasi bado.",
    "status_pending": "inasubiri",
    "status_confirmed": "imethibitishwa",
    "status_cancelled": "imeghairiwa",
    "status_completed": "imekamilika",
}