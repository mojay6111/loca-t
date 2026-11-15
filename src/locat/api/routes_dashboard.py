"""Dashboard and advice endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from locat.db.models import Property
from locat.db.session import get_db
from locat.services.advice_service import MAX_DAYS, advice_for_property

router = APIRouter(tags=["dashboard"])


@router.get("/advice/{listing_code}")
def get_advice(listing_code: str, days: int = 28, db: Session = Depends(get_db)):
    prop = db.scalar(select(Property).where(Property.listing_code == listing_code.upper()))
    if prop is None:
        raise HTTPException(status_code=404, detail="unknown listing code")
    try:
        advice = advice_for_property(prop, days)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

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