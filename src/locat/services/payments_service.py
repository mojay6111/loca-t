"""M-Pesa deposits: a console simulator for development, Africa's Talking for real."""
import uuid

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from locat.config import get_settings
from locat.db.models import Booking, Payment
from locat.services.booking_service import (
    booking_ref,
    cancel_booking,
    confirm_and_notify,
    notify_payment_failed,
)

AT_CHECKOUT_URLS = {
    "sandbox": "https://payments.sandbox.africastalking.com/mobile/checkout/request",
    "live": "https://payments.africastalking.com/mobile/checkout/request",
}
SUCCESS_WORDS = {"success", "completed"}
STILL_PENDING_WORDS = {"pending", "pendingconfirmation", "queued", ""}


class PaymentStartError(Exception):
    """The M-Pesa request could not be started (nothing was charged)."""


def _start_console(payment: Payment, booking: Booking) -> str:
    ref = f"SIM-{uuid.uuid4().hex[:12]}"
    print(
        f"\n[M-PESA simulator] STK push to {payment.phone}: "
        f"pay KES {payment.amount:.0f} for {booking_ref(booking)}\n"
        f"  provider_ref = {ref}\n"
        f"  approve: curl -X POST "
        f"'http://127.0.0.1:8020/payments/simulate/{booking.id}?outcome=success'\n"
        f"  decline: curl -X POST "
        f"'http://127.0.0.1:8020/payments/simulate/{booking.id}?outcome=failed'\n",
        flush=True,
    )
    return ref


def _start_africastalking(payment: Payment, booking: Booking) -> str:
    settings = get_settings()
    if not settings.at_api_key or not settings.at_payment_product:
        raise PaymentStartError("AT_API_KEY and AT_PAYMENT_PRODUCT must be set in .env")

    env = "sandbox" if settings.at_username == "sandbox" else "live"
    body = {
        "username": settings.at_username,
        "productName": settings.at_payment_product,
        "phoneNumber": payment.phone,
        "currencyCode": "KES",
        "amount": payment.amount,
        "metadata": {"booking_id": str(booking.id), "ref": booking_ref(booking)},
    }
    headers = {
        "apiKey": settings.at_api_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    try:
        response = httpx.post(AT_CHECKOUT_URLS[env], json=body, headers=headers, timeout=20)
    except httpx.HTTPError as exc:
        raise PaymentStartError(f"network error: {exc}") from exc

    print(f"[AT checkout] HTTP {response.status_code}: {response.text}", flush=True)
    try:
        data = response.json()
    except ValueError as exc:
        raise PaymentStartError("response was not JSON") from exc

    if data.get("status") != "PendingConfirmation" or not data.get("transactionId"):
        raise PaymentStartError(f"unexpected response: {data}")
    return data["transactionId"]


def initiate_deposit(db: Session, booking: Booking) -> Payment:
    """Ask the guest's phone to pay the deposit. Releases the booking on failure."""
    payment = Payment(
        booking_id=booking.id,
        phone=booking.guest.phone,
        amount=booking.deposit_amount,
        status="pending",
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)

    settings = get_settings()
    try:
        if settings.payment_mode == "africastalking":
            ref = _start_africastalking(payment, booking)
        else:
            ref = _start_console(payment, booking)
    except PaymentStartError:
        payment.status = "failed"
        db.commit()
        cancel_booking(db, booking.id)
        raise

    payment.provider_ref = ref
    db.commit()
    db.refresh(payment)
    return payment


def apply_payment_result(db: Session, provider_ref: str, status_text: str) -> Payment | None:
    """Apply a final payment result. Safe to call twice for the same payment."""
    payment = db.scalar(select(Payment).where(Payment.provider_ref == provider_ref))
    if payment is None:
        return None
    if payment.status != "pending":
        return payment  # duplicate callback: already handled

    word = status_text.strip().lower()
    if word in STILL_PENDING_WORDS:
        return payment  # not a final result yet

    if word in SUCCESS_WORDS:
        payment.status = "success"
        db.commit()
        booking = confirm_and_notify(db, payment.booking_id)
        if booking is None or booking.status != "confirmed":
            print(
                f"[WARNING] payment {payment.id} succeeded but booking "
                f"{payment.booking_id} is not confirmed: needs a refund",
                flush=True,
            )
    else:
        payment.status = "failed"
        db.commit()
        booking = cancel_booking(db, payment.booking_id)
        if booking is not None:
            notify_payment_failed(db, booking)

    db.refresh(payment)
    return payment