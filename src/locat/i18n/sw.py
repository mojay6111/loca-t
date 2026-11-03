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
}