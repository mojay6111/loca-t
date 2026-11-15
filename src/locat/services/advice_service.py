"""Occupancy outlook and price advice for Loca-T properties.

Wraps the forecaster (notebook 04) and the advisor (notebook 05) for the app. The history
comes from data/processed/synthetic_occupancy_demo.csv. IT IS SYNTHETIC until real bookings exist.
"""
from __future__ import annotations

from datetime import date
from functools import lru_cache
from pathlib import Path

import pandas as pd

from locat.config import get_settings
from locat.forecasting import advisor
from locat.forecasting.features import build_features
from locat.forecasting.model import OccupancyForecaster

HISTORY_FILE = "synthetic_occupancy_demo.csv"
MAX_DAYS = 60  # the validated horizon


@lru_cache
def _load():
    folder = Path(get_settings().data_dir)
    cal = pd.read_csv(folder / "calendar_daily.csv", parse_dates=["date"])
    seasonal = pd.read_csv(folder / "seasonal_index.csv")
    idx_map = dict(zip(seasonal["month_number"], seasonal["seasonal_index"]))
    feats = build_features(cal, idx_map)
    quantiles = pd.read_csv(folder / "forecast_interval_quantiles.csv", index_col=0)
    history = pd.read_csv(folder / HISTORY_FILE, parse_dates=["date"])
    occ = history.pivot(index="date", columns="destination", values="occupancy")
    forecaster = OccupancyForecaster(feats, quantiles).fit(occ)
    return forecaster, feats, occ


def today() -> pd.Timestamp:
    raw = get_settings().demo_today
    return pd.Timestamp(raw) if raw else pd.Timestamp(date.today())


def advice_for_property(prop, days: int = 28, start=None) -> pd.DataFrame:
    """Night-by-night outlook and advice for a property.

    prop needs .destination and .base_price. The forecast starts today (or at `start`) but never
    before the day after the last history day. Days are limited to the validated 60 and to the
    end of the calendar data.
    """
    forecaster, feats, occ = _load()
    if prop.destination not in forecaster.models:
        raise ValueError(f"no forecast model for destination {prop.destination!r}")

    first = (
        max(today(), forecaster.last_date + pd.Timedelta(days=1))
        if start is None else pd.Timestamp(start)
    )
    last_available = feats.index.max()
    if first > last_available:
        raise ValueError(f"calendar data ends on {last_available.date()}")
    days = max(1, min(int(days), MAX_DAYS, (last_available - first).days + 1))

    forecast = forecaster.forecast(prop.destination, horizon=days, start=first)
    typical = advisor.typical_occupancy(occ[prop.destination])
    return advisor.advise(forecast, feats, typical, prop.base_price)