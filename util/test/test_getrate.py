from pytest import approx
from util import getrate


def test_getrate_ocean_oneday():
    r = getrate.getrate("OCEAN", "2022-01-20", "2022-01-20")
    assert r == approx(0.75, 0.1)  # coingecko numbers


def test_getrate_ocean_oneweek():
    r = getrate.getrate("OCEAN", "2022-01-20", "2022-01-26")
    assert r == approx(0.65, 0.1)  # coingecko numbers


def test_getrate_h2o():
    assert getrate.getrate("h2o", "2022-05-13", "2022-05-25") == approx(1.50, 0.1)


def test_start_after_fin():
    p = getrate.getrate("OCEAN", "2021-01-26", "2021-12-20")
    assert p == approx(0.89, 0.1) #coingecko numbers


def test_coingeckoRate_bitcoin():
    r = getrate.getrate("BTC", "2022-01-31", "2022-01-31")
    assert r == approx(37983.15, 0.1)


def test_coingeckoRate_ocean():
    r = getrate.getrate("OCEAN", "2022-01-31", "2022-01-31")
    assert r == approx(0.58, 0.1)
