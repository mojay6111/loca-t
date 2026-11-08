"""Per-destination occupancy forecaster: ridge on log occupancy with calendar features,
plus empirical prediction intervals from past backtest errors."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

CAP = 0.98
ALPHA = 1.0


def fit_destination(features: pd.DataFrame, occupancy: pd.Series):
    """Fit on an occupancy history (a Series indexed by date)."""
    model = make_pipeline(StandardScaler(), Ridge(alpha=ALPHA))
    model.fit(features.loc[occupancy.index], np.log(occupancy.to_numpy()))
    return model


def predict_occupancy(model, features: pd.DataFrame, dates) -> pd.Series:
    pred = np.exp(model.predict(features.loc[dates]))
    return pd.Series(np.clip(pred, 0.01, CAP), index=dates)


def add_interval(point: pd.Series, q_lo: float, q_hi: float) -> pd.DataFrame:
    return pd.DataFrame({
        "forecast": point,
        "lower": np.clip(point * np.exp(q_lo), 0.0, CAP),
        "upper": np.clip(point * np.exp(q_hi), 0.0, CAP),
    })


@dataclass
class OccupancyForecaster:
    features: pd.DataFrame          # from build_features, covering history and future
    quantiles: pd.DataFrame         # index: destination; columns: q10, q90 (log errors)
    models: dict = field(default_factory=dict)
    last_date: pd.Timestamp | None = None

    def fit(self, occupancy_wide: pd.DataFrame) -> "OccupancyForecaster":
        self.models = {
            d: fit_destination(self.features, occupancy_wide[d].dropna())
            for d in occupancy_wide.columns
        }
        self.last_date = occupancy_wide.index.max()
        return self

    def forecast(self, destination: str, horizon: int = 28, start=None) -> pd.DataFrame:
        """Forecast with an 80% interval. Default start: the day after the last history day."""
        first = self.last_date + pd.Timedelta(days=1) if start is None else pd.Timestamp(start)
        dates = pd.date_range(first, periods=horizon)
        point = predict_occupancy(self.models[destination], self.features, dates)
        q = self.quantiles.loc[destination]
        out = add_interval(point, q["q10"], q["q90"])
        out.index.name = "date"
        return out