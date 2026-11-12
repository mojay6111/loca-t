"""Turn a demand forecast into advice for one property.

Rules (checked in notebook 05):
1. No default price cuts.
2. Confident raise: only where the model's unclipped demand exceeds the rooms. Size:
   (D / cap) ** (1 / 1.4) - 1, rounded down to a multiple of 5%, minimum 5%, maximum 25%.
   It is never above the break-even raise for guests with price elasticity -2.
3. Test: +5% on busy nights (model demand at or above 80% of rooms) when no confident
   raise applies. An experiment: the host's answers are how the system learns price
   sensitivity.
4. Quiet nights get a non-price suggestion (a promotion), never a price cut.

Reasons are qualitative on purpose. Numbers are quoted only where the effect was recovered
well (see the model card).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

CAP = 0.98
EPS_MID = -1.4
RAISE_STEP, MIN_RAISE, MAX_RAISE = 0.05, 0.05, 0.25
TEST_THRESHOLD, TEST_RAISE = 0.80, 0.05
BUSY_RATIO, QUIET_RATIO = 1.20, 0.80
PRICE_STEP = 50  # KES; suggested prices are rounded down to this

REASON_FLAGS = [
    ("school_out", "school holidays"),
    ("is_long_weekend", "long weekend"),
    ("easter_period", "Easter"),
    ("fri_sat_night", "weekend"),
    ("payday_window", "payday week"),
]


def confident_raise(demand) -> np.ndarray:
    """Raise (as a fraction) for demand given as a share of rooms; 0 when none applies."""
    D = np.asarray(demand, dtype=float)
    r = np.where(D > CAP, (D / CAP) ** (1 / abs(EPS_MID)) - 1, 0.0)
    r = np.floor(r / RAISE_STEP + 1e-9) * RAISE_STEP
    return np.where(r < MIN_RAISE, 0.0, np.minimum(r, MAX_RAISE))


def typical_occupancy(history: pd.Series, days: int = 365) -> float:
    """The property's usual occupancy: the mean of its last `days` days."""
    return float(history.tail(days).mean())


def level_labels(forecast, typical: float) -> np.ndarray:
    ratio = np.asarray(forecast, dtype=float) / typical
    return np.where(ratio >= BUSY_RATIO, "busy", np.where(ratio <= QUIET_RATIO, "quiet", "normal"))


def _reasons(row) -> str:
    names = [label for col, label in REASON_FLAGS if row.get(col, 0) == 1]
    return ", ".join(names) if names else "regular day"


def advise(forecast: pd.DataFrame, flags: pd.DataFrame, typical: float, base_price: float) -> pd.DataFrame:
    """One row per night.

    forecast: output of OccupancyForecaster.forecast (needs forecast, lower, upper, demand).
    flags: calendar flags indexed by date (school_out, is_long_weekend, easter_period,
           fri_sat_night, payday_window).
    typical: the property's usual occupancy (share of rooms).
    base_price: the current nightly price in KES.
    """
    demand = forecast["demand"].to_numpy(dtype=float)
    raise_pct = confident_raise(demand)
    level = level_labels(forecast["forecast"], typical)

    is_raise = raise_pct > 0
    is_test = (demand >= TEST_THRESHOLD) & ~is_raise
    is_quiet = (level == "quiet") & ~is_raise & ~is_test

    action = np.select([is_raise, is_test, is_quiet], ["raise", "test", "promote"], default="hold")
    change = np.where(is_raise, raise_pct, np.where(is_test, TEST_RAISE, 0.0))
    target = base_price * (1 + change)
    price = np.where(
        change > 0,
        np.maximum(np.floor(target / PRICE_STEP) * PRICE_STEP, base_price),
        base_price,
    )

    return pd.DataFrame(
        {
            "forecast": forecast["forecast"].to_numpy(),
            "lower": forecast["lower"].to_numpy(),
            "upper": forecast["upper"].to_numpy(),
            "level": level,
            "action": action,
            "price_change": change,
            "suggested_price": price.astype(int),
            "reasons": flags.loc[forecast.index].apply(_reasons, axis=1).to_numpy(),
        },
        index=forecast.index,
    )