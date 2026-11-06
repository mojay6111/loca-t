"""M-Pesa deposits: a console simulator for development, Daraja STK push for the sandbox."""
import base64
import time
import uuid
from datetime import datetime

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

SUCCESS_WORDS = {"success", "completed"}
STILL_PENDING_WORDS = {"pending", "pendingconfirmation", "queued", ""}

# Daraja access tokens last about an hour; reuse one so USSD stays fast.
_token_cache: dict = {"token": None, "expires_at": 0.0}


class PaymentStartError(Exception):
    """The M-Pesa request could not be started (nothing was charged)."""


# ---------- console simulator ----------

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


# ---------- Safaricom Daraja (M-Pesa Express) ----------

def _daraja_token() -> str:
    settings = get_settings()
    if _token_cache["token"] and time.time() < _token_cache["expires_at"]:
        return _token_cache["token"]

    if not settings.daraja_consumer_key or not settings.daraja_consumer_secret:
        raise PaymentStartError(
            "DARAJA_CONSUMER_KEY and DARAJA_CONSUMER_SECRET must be set in .env"
        )

    try:
        response = httpx.get(
            f"{settings.daraja_base_url}/oauth/v1/generate",
            params={"grant_type": "client_credentials"},
            auth=(settings.daraja_consumer_key, settings.daraja_consumer_secret),
            timeout=15,
        )
    except httpx.HTTPError as exc:
        raise PaymentStartError(f"token request failed: {exc}") from exc

    if response.status_code != 200:
        print(f"[Daraja token] HTTP {response.status_code}: {response.text}", flush=True)
        raise PaymentStartError("could not get a Daraja access token")

    try:
        data = response.json()
        token = data["access_token"]
        lifetime = int(data.get("expires_in", 3599))
    except (ValueError, KeyError) as exc:
        raise PaymentStartError("unexpected token response") from exc

    _token_cache["token"] = token
    _token_cache["expires_at"] = time.time() + lifetime - 60
    return token


def _start_daraja(payment: Payment, booking: Booking) -> str:
    settings = get_settings()
    if not settings.daraja_passkey:
        raise PaymentStartError("DARAJA_PASSKEY must be set in .env")
    if not settings.public_base_url or not settings.payment_callback_secret:
        raise PaymentStartError(
            "PUBLIC_BASE_URL and PAYMENT_CALLBACK_SECRET must be set in .env"
        )

    token = _daraja_token()
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    password = base64.b64encode(
        f"{settings.daraja_shortcode}{settings.daraja_passkey}{timestamp}".encode()
    ).decode()
    phone = payment.phone.lstrip("+")  # Daraja wants 2547XXXXXXXX
    if settings.daraja_test_msisdn and "sandbox" in settings.daraja_base_url:
        print(
            f"[Daraja STK] sandbox override: prompting the test number "
            f"instead of {payment.phone}",
            flush=True,
        )
        phone = settings.daraja_test_msisdn.lstrip("+")
        
    body = {
        "BusinessShortCode": settings.daraja_shortcode,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(round(payment.amount)),
        "PartyA": phone,
        "PartyB": settings.daraja_shortcode,
        "PhoneNumber": phone,
        "CallBackURL": (
            f"{settings.public_base_url.rstrip('/')}"
            f"/payments/callback/{settings.payment_callback_secret}"
        ),
        "AccountReference": booking_ref(booking),
        "TransactionDesc": "Deposit",
    }

    try:
        response = httpx.post(
            f"{settings.daraja_base_url}/mpesa/stkpush/v1/processrequest",
            json=body,
            headers={"Authorization": f"Bearer {token}"},
            timeout=20,
        )
    except httpx.HTTPError as exc:
        raise PaymentStartError(f"network error: {exc}") from exc

    # We print the response only, never the request (it holds the password and secret).
    print(f"[Daraja STK] HTTP {response.status_code}: {response.text}", flush=True)
    if response.status_code == 401:
        _token_cache["token"] = None  # force a fresh token next time

    try:
        data = response.json()
    except ValueError as exc:
        raise PaymentStartError("response was not JSON") from exc

    if str(data.get("ResponseCode")) != "0" or not data.get("CheckoutRequestID"):
        raise PaymentStartError(f"request not accepted: {data}")
    return data["CheckoutRequestID"]


# ---------- shared logic ----------

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

    mode = get_settings().payment_mode
    try:
        if mode == "daraja":
            ref = _start_daraja(payment, booking)
        elif mode == "console":
            ref = _start_console(payment, booking)
        else:
            raise PaymentStartError(f"unknown PAYMENT_MODE '{mode}'")
    except PaymentStartError as exc:
        print(f"[payment start failed] {exc}", flush=True)
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