"""Calendar features for the occupancy model. All are known in advance for any date."""
from __future__ import annotations

import numpy as np
import pandas as pd

from locat.forecasting.synthetic import smooth_intl_index

FLAG_COLS = [
    "fri_sat_night", "school_out", "is_long_weekend", "easter_period", "payday_window",
]


def build_features(cal: pd.DataFrame, idx_by_month: dict) -> pd.DataFrame:
    """One row per date: five calendar flags, the log of the smoothed international
    index, three annual sine/cosine pairs and a linear trend (years since 2024-01-01)."""
    cal = cal.sort_values("date").reset_index(drop=True)
    feat = pd.DataFrame(index=pd.DatetimeIndex(cal["date"], name="date"))
    for c in FLAG_COLS:
        feat[c] = cal[c].astype(float).to_numpy()
    feat["log_intl"] = np.log(smooth_intl_index(pd.Series(feat.index), idx_by_month))
    doy = feat.index.dayofyear.to_numpy()
    for k in (1, 2, 3):
        feat[f"sin{k}"] = np.sin(2 * np.pi * k * doy / 365.25)
        feat[f"cos{k}"] = np.cos(2 * np.pi * k * doy / 365.25)
    feat["trend"] = ((feat.index - pd.Timestamp("2024-01-01")).days / 365.25).to_numpy()
    return feat