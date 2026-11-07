"""Synthetic daily occupancy for Loca-T.

EVERYTHING PRODUCED HERE IS SYNTHETIC. The inputs (`params`, `month_adjust`,
`settings`) are assumptions, not measurements. The real-data evidence is the KNBS
arrivals work in notebook 01.

Model, per destination and day:

    latent    = base x growth x mixture x own_season x noise
    mixture   = intl_share x intl_smooth + (1 - intl_share) x domestic
    occupancy = min(latent, occupancy_cap)

`domestic` multiplies the weekend, school-break, long-weekend, Easter and payday
boosts, and is divided by its own average over the history, so `base` keeps its
meaning ("typical share of rooms filled").
"""
from __future__ import annotations

import numpy as np
import pandas as pd

MONTH_LABELS = [pd.Timestamp(2000, m, 1).strftime("%b") for m in range(1, 13)]
CALENDAR_COLUMNS = [
    "date", "month", "fri_sat_night", "school_out",
    "is_long_weekend", "easter_period", "payday_window",
]


def smooth_intl_index(dates: pd.Series, idx_by_month: dict) -> np.ndarray:
    """Interpolate the monthly index linearly between mid-month anchors."""
    anchors = pd.date_range("2023-12-01", "2027-12-01", freq="MS") + pd.Timedelta(days=14)
    values = [idx_by_month[a.month] for a in anchors]
    return np.interp(
        dates.map(pd.Timestamp.toordinal),
        [a.toordinal() for a in anchors],
        values,
    )


def generate_history(
    cal: pd.DataFrame,
    params: pd.DataFrame,
    month_adjust: pd.DataFrame,
    settings: dict,
    idx_by_month: dict,
    history_end: pd.Timestamp,
) -> pd.DataFrame:
    """Return a long table: date, destination, latent_demand, occupancy, source.

    `params` has one column per destination; `month_adjust` has one row per
    destination and one column per month label. `settings` needs: annual_growth,
    noise_ar, noise_sd, seed, easter_extra, payday_boost and occupancy_cap.
    """
    cal = cal[CALENDAR_COLUMNS].reset_index(drop=True)
    intl_smooth = smooth_intl_index(cal["date"], idx_by_month)
    years = (cal["date"] - pd.Timestamp("2024-01-01")).dt.days / 365.25
    growth = ((1 + settings["annual_growth"]) ** years).to_numpy()
    in_history = (cal["date"] <= history_end).to_numpy()

    rng = np.random.default_rng(settings["seed"])
    phi, sd = settings["noise_ar"], settings["noise_sd"]

    frames = []
    for dest in params.columns:
        p = params[dest]

        domestic = (
            np.where(cal["fri_sat_night"] == 1, p["weekend_boost"], 1.0)
            * np.where(cal["school_out"] == 1, p["school_boost"], 1.0)
            * np.where(cal["is_long_weekend"] == 1, p["longwknd_boost"], 1.0)
            * np.where(cal["easter_period"] == 1, settings["easter_extra"], 1.0)
            * np.where(cal["payday_window"] == 1, settings["payday_boost"], 1.0)
        )
        domestic = domestic / domestic[in_history].mean()

        mixture = p["intl_share"] * intl_smooth + (1 - p["intl_share"]) * domestic
        own_season = cal["month"].map(
            lambda m: month_adjust.loc[dest, MONTH_LABELS[m - 1]]
        ).to_numpy()

        # AR(1) noise on the log scale: neighbouring days share some luck
        z = rng.standard_normal(len(cal))
        e = np.zeros(len(cal))
        for t in range(1, len(cal)):
            e[t] = phi * e[t - 1] + np.sqrt(1 - phi**2) * z[t]
        noise = np.exp(sd * e - 0.5 * sd**2)

        latent = p["base_occupancy"] * growth * mixture * own_season * noise
        frames.append(pd.DataFrame({
            "date": cal["date"],
            "destination": dest,
            "latent_demand": latent,
            "occupancy": np.minimum(latent, settings["occupancy_cap"]),
        }))

    out = pd.concat(frames, ignore_index=True)
    out = out[out["date"] <= history_end].reset_index(drop=True)
    out["source"] = "synthetic"
    return out