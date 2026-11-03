"""English USSD/SMS strings. Keep each USSD screen under ~180 characters."""

STRINGS = {
    "main_menu": (
        "Karibu Loca-T\n"
        "1. Find a stay\n"
        "2. List my place\n"
        "3. My bookings\n"
        "4. Lugha/Language"
    ),
    "coming_soon": "This feature is coming soon.",
    "invalid": "Invalid input. Please dial again.",
    "cancelled": "Cancelled. Dial again anytime.",
    "ask_property_name": "Name of your place:",
    "ask_destination": "Where is it?\n{options}",
    "ask_rooms": "How many rooms?",
    "ask_price": "Price per night (KES):",
    "confirm_listing": (
        "Confirm:\n{name}, {destination}\n"
        "{rooms} rooms @ KES {price}\n"
        "1. Confirm\n2. Cancel"
    ),
    "listing_saved": "You are live! Your code: {code}",
    "language_menu": "Choose language:\n1. English\n2. Kiswahili",
    "language_saved": "Language set to English.",
}