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
    
    "find_destination": "Where to?\n{options}",
    "pick_stay": "Pick a stay:\n{options}",
    "no_listings": "No stays listed there yet. Try another place.",
    "ask_checkin": "Check-in date:\n1. {d1}\n2. {d2}\n3. Other date",
    "ask_date": "Type date as DDMM (e.g. 2811):",
    "ask_nights": "How many nights?",
    "ask_guests": "How many guests?",
    "no_rooms": "Sorry, no rooms free for those dates.",
    "confirm_booking": (
        "{name}\n{check_in}, {nights} night(s), {guests} guest(s)\n"
        "Total KES {total}\nDeposit KES {deposit}\n"
        "1. Confirm\n2. Cancel"
    ),
    "booking_saved": "Reserved! Ref {ref}. Deposit KES {deposit}. Payment steps by SMS soon.",
    "my_bookings": "Your bookings:\n{lines}",
    "no_bookings": "You have no bookings yet.",
    "status_pending": "pending",
    "status_confirmed": "confirmed",
    "status_cancelled": "cancelled",
    "status_completed": "completed",

    "sms_guest_confirmed": (
        "Booking confirmed! {name}, {destination}. {check_in} to {check_out}, "
        "{guests} guest(s). Ref {ref}. Paid KES {deposit}, balance KES {balance} "
        "on arrival. See you soon!"
    ),
    "sms_host_new_booking": (
        "New booking {ref}: {guests} guest(s), {check_in} to {check_out}. "
        "Deposit KES {deposit} received. Your share of the total: KES {host_amount}."
    ),
}