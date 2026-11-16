"""Dashboard and advice endpoints."""
import secrets

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from locat.config import get_settings
from locat.db.models import Property
from locat.db.session import get_db
from locat.services.advice_service import MAX_DAYS, advice_for_property, render_outlook
from locat.services.sms_service import send_sms

router = APIRouter(tags=["dashboard"])


def _property_or_404(db: Session, listing_code: str) -> Property:
    prop = db.scalar(select(Property).where(Property.listing_code == listing_code.upper()))
    if prop is None:
        raise HTTPException(status_code=404, detail="unknown listing code")
    return prop


def _advice_or_400(prop: Property, days: int):
    try:
        return advice_for_property(prop, days)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _require_admin(token: str) -> None:
    expected = get_settings().admin_token
    if not expected or not secrets.compare_digest(token, expected):
        raise HTTPException(status_code=404)


@router.get("/advice/{listing_code}")
def get_advice(listing_code: str, days: int = 28, db: Session = Depends(get_db)):
    prop = _property_or_404(db, listing_code)
    advice = _advice_or_400(prop, days)
    nights = [
        {
            "date": day.strftime("%Y-%m-%d"),
            "day": day.strftime("%a %d %b"),
            "forecast_pct": round(100 * row["forecast"]),
            "lower_pct": round(100 * row["lower"]),
            "upper_pct": round(100 * row["upper"]),
            "level": row["level"],
            "action": row["action"],
            "suggested_price": int(row["suggested_price"]),
            "reasons": row["reasons"],
        }
        for day, row in advice.iterrows()
    ]
    return {
        "listing_code": prop.listing_code,
        "property": prop.name,
        "destination": prop.destination,
        "base_price": prop.base_price,
        "synthetic_data": True,
        "validated_horizon_days": MAX_DAYS,
        "nights": nights,
    }


@router.get("/advice/{listing_code}/digest")
def preview_digest(listing_code: str, kind: str = "sms", db: Session = Depends(get_db)):
    """The outlook text for a property, in its host's language, without sending anything."""
    prop = _property_or_404(db, listing_code)
    advice = _advice_or_400(prop, MAX_DAYS)
    kind = kind if kind in ("sms", "ussd") else "sms"
    text = render_outlook(advice, prop.name, prop.host.language, kind)
    return {"language": prop.host.language, "kind": kind, "length": len(text), "text": text}


@router.post("/advice/{listing_code}/send")
def send_digest(
    listing_code: str,
    x_admin_token: str = Header(default=""),
    db: Session = Depends(get_db),
):
    """Send the SMS digest to the host. Needs the X-Admin-Token header."""
    _require_admin(x_admin_token)
    prop = _property_or_404(db, listing_code)
    advice = _advice_or_400(prop, MAX_DAYS)
    host = prop.host
    text = render_outlook(advice, prop.name, host.language, "sms")
    return {
        "sent": send_sms(host.phone, text),
        "to": host.phone,
        "language": host.language,
        "length": len(text),
        "text": text,
    }