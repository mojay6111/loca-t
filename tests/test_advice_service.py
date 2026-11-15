from pathlib import Path

import pandas as pd
import pytest

from locat.services import advice_service as svc

pytestmark = pytest.mark.skipif(
    not Path("data/processed/synthetic_occupancy_demo.csv").exists(),
    reason="demo data not generated",
)


class FakeProperty:
    destination = "Naivasha"
    base_price = 4500.0


def test_festive_nights_and_no_cuts():
    a = svc.advice_for_property(FakeProperty(), days=60, start="2026-11-26")
    assert len(a) == 60
    assert (a["price_change"] >= 0).all()
    xmas = a.loc["2026-12-25":"2026-12-26"]
    assert (xmas["action"] == "test").all()
    assert (xmas["suggested_price"] == 4700).all()


def test_days_are_clipped_to_the_calendar():
    a = svc.advice_for_property(FakeProperty(), days=500, start="2027-03-01")
    assert len(a) == 31
    assert a.index.max() == pd.Timestamp("2027-03-31")


def test_start_beyond_the_calendar_raises():
    with pytest.raises(ValueError):
        svc.advice_for_property(FakeProperty(), days=7, start="2027-06-01")