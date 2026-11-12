import numpy as np
import pandas as pd

from locat.forecasting import advisor as adv


def _forecast(demand):
    demand = np.asarray(demand, dtype=float)
    idx = pd.date_range("2026-12-01", periods=len(demand))
    f = pd.DataFrame({"demand": demand}, index=idx)
    f["forecast"] = np.clip(demand, 0.01, adv.CAP)
    f["lower"] = f["forecast"] * 0.85
    f["upper"] = np.minimum(f["forecast"] * 1.15, adv.CAP)
    return f


def _flags(index, **overrides):
    base = {"school_out": 0, "is_long_weekend": 0, "easter_period": 0,
            "fri_sat_night": 0, "payday_window": 0}
    base.update(overrides)
    return pd.DataFrame(base, index=index)


def test_confident_raise_values():
    r = adv.confident_raise([0.50, 0.98, 1.03, 1.09, 1.13, 3.0])
    assert np.allclose(r, [0.0, 0.0, 0.0, 0.05, 0.10, 0.25])


def test_never_above_break_even_at_eps_minus_2():
    D = np.linspace(0.5, 2.0, 301)
    r = adv.confident_raise(D)
    assert (r <= np.maximum(D / adv.CAP - 1, 0) + 1e-9).all()


def test_level_labels():
    labels = adv.level_labels([0.30, 0.45, 0.62, 0.70], typical=0.50)
    assert labels.tolist() == ["quiet", "normal", "busy", "busy"]


def test_advise_actions_and_prices():
    f = _forecast([0.30, 0.45, 0.82, 1.10])
    a = adv.advise(f, _flags(f.index), typical=0.50, base_price=4500)
    assert a["action"].tolist() == ["promote", "hold", "test", "raise"]
    assert np.allclose(a["price_change"], [0.0, 0.0, 0.05, 0.05])
    assert a["suggested_price"].tolist() == [4500, 4500, 4700, 4700]


def test_never_cuts_and_gives_reasons():
    f = _forecast(np.linspace(0.1, 1.4, 40))
    a = adv.advise(f, _flags(f.index, school_out=1, fri_sat_night=1), typical=0.5, base_price=3000)
    assert (a["price_change"] >= 0).all()
    assert (a["suggested_price"] >= 3000).all()
    assert (a["reasons"] == "school holidays, weekend").all()