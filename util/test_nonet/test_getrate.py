import pytest
from enforce_typing import enforce_types
from pytest import approx

from util import getrate


@enforce_types
@pytest.mark.skip(reason="This fails in GH Actions for some reason, passes on local")
def test_getBinanceRate_OCEAN_sameday():
    r = getrate.getBinanceRate("OCEAN", "2022-01-20", "2022-01-20")
    assert r == approx(0.75, 0.1)


@enforce_types
def test_getCoingeckoRate_OCEAN_sameday():
    r = getrate.getCoingeckoRate("OCEAN", "2022-01-20", "2022-01-20")
    assert r == approx(0.75, 0.1)


@enforce_types
def test_getrate_OCEAN_sameday():
    r = getrate.getrate("OCEAN", "2022-01-20", "2022-01-20")
    assert r == approx(0.75, 0.1)


@enforce_types
def test_getrate_OCEAN_oneweek():
    r = getrate.getrate("OCEAN", "2022-01-20", "2022-01-26")
    assert r == approx(0.65, 0.1)


@enforce_types
def test_getrate_H2O():
    r = getrate.getrate("H2O", "2022-05-13", "2022-05-25")
    assert r == approx(1.50, 0.1)


@enforce_types
def test_getrate_BTC():
    r = getrate.getrate("BTC", "2022-01-31", "2022-01-31")
    assert r == approx(37983.15, 0.1)


@enforce_types
def test_start_after_fin():
    p = getrate.getrate("OCEAN", "2021-01-26", "2021-12-20")
    assert p == approx(0.89, 0.1)
