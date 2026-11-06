"""Payment callback (called by Safaricom Daraja) and a dev-only simulator."""
import json
import secrets
from urllib.parse import parse_qs

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from locat.config import get_settings
from locat.db.models import Payment
from locat.db.session import get_db
from locat.services.payments_service import apply_payment_result

router = APIRouter(prefix="/payments", tags=["payments"])


async def _read_payload(request: Request) -> dict:
    """Accept JSON or form-encoded bodies, and log exactly what arrived."""
    text = (await request.body()).decode("utf-8", errors="replace")
    print(
        f"[payment callback raw] content-type="
        f"{request.headers.get('content-type')} body={text}",
        flush=True,
    )
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except ValueError:
        pass
    return {key: values[0] for key, values in parse_qs(text).items()}


def _extract_result(payload: dict) -> tuple[str, str]:
    """Return (provider_ref, status_text).

    Daraja nests the result in Body.stkCallback (ResultCode 0 = paid; anything
    else, such as 1032 'cancelled by user', is a failure). The flat
    {transactionId, status} form is kept for manual tests.
    """
    body = payload.get("Body")
    stk = body.get("stkCallback") if isinstance(body, dict) else None
    if isinstance(stk, dict):
        ref = str(stk.get("CheckoutRequestID", ""))
        status = "Success" if str(stk.get("ResultCode")) == "0" else "Failed"
        return ref, status
    return str(payload.get("transactionId", "")), str(payload.get("status", ""))


@router.post("/callback/{secret}")
async def payment_callback(
    secret: str, request: Request, db: Session = Depends(get_db)
):
    expected = get_settings().payment_callback_secret
    if not expected or not secrets.compare_digest(secret, expected):
        raise HTTPException(status_code=404)

    payload = await _read_payload(request)
    provider_ref, status_text = _extract_result(payload)
    payment = apply_payment_result(db, provider_ref, status_text)
    return {
        "ResultCode": 0,
        "ResultDesc": "Accepted",
        "received": True,
        "matched": payment is not None,
    }


@router.post("/simulate/{booking_id}")
def simulate_payment(booking_id: int, outcome: str = "success", db: Session = Depends(get_db)):
    """Console mode only: pretend the guest approved or declined the M-Pesa prompt."""
    if get_settings().payment_mode != "console":
        raise HTTPException(status_code=404)

    payment = db.scalar(
        select(Payment)
        .where(Payment.booking_id == booking_id, Payment.status == "pending")
        .order_by(Payment.id.desc())
    )
    if payment is None or not payment.provider_ref:
        raise HTTPException(status_code=404, detail="no pending payment for that booking")

    result = apply_payment_result(
        db, payment.provider_ref, "Success" if outcome == "success" else "Failed"
    )
    return {"booking_id": booking_id, "payment_status": result.status}