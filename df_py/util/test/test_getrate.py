from unittest.mock import patch

import pytest
from enforce_typing import enforce_types
from pytest import approx

from df_py.util import getrate


@enforce_types
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

    # special case in coingecko
    r = getrate.getCoingeckoRate("H2O", "2022-05-13", "2022-05-25")
    assert r == 1.618


@enforce_types
def test_getrate_fallback():
    with patch("df_py.util.getrate.getBinanceRate") as mock1:
        mock1.return_value = None
        r = getrate.getrate("OCEAN", "2022-01-20", "2022-01-20")

    # from goingecko
    assert r == approx(0.75, 0.1)

    with patch("df_py.util.getrate.getBinanceRate") as mock1:
        mock1.return_value = None
        with patch("df_py.util.getrate.getCoingeckoRate") as mock2:
            mock2.return_value = None
            r = getrate.getrate("OCEAN", "2022-01-20", "2022-01-20")

    assert r is None


@pytest.mark.skip(reason="Temporarily skipping, fails on GH for some reason")
@enforce_types
def test_getrate_BTC():
    r = getrate.getrate("BTC", "2022-01-31", "2022-01-31")
    assert r == approx(37983.15, 0.1)


@pytest.mark.skip(reason="Temporarily skipping, fails on GH for some reason")
@enforce_types
def test_start_after_fin():
    p = getrate.getrate("OCEAN", "2021-01-26", "2021-12-20")
    assert p == approx(0.89, 0.1)


@enforce_types
def test_getBinanceRate_empty():
    with patch("df_py.util.getrate.requests.get") as mock1:
        mock1.return_value.json.return_value = {}
        r = getrate.getBinanceRate("OCEAN", "2022-01-20", "2022-01-20")

    assert r is None

    with patch("df_py.util.getrate.requests.get") as mock1:
        mock1.side_effect = Exception("test")
        r = getrate.getBinanceRate("OCEAN", "2022-01-20", "2022-01-20")

    assert r is None


@enforce_types
def test_getCoingeckoRate_empty():
    with patch("df_py.util.getrate.requests.get") as mock1:
        mock1.return_value.json.return_value = {}
        r = getrate.getCoingeckoRate("OCEAN", "2022-01-20", "2022-01-20")

    assert r is None

    with patch("df_py.util.getrate.requests.get") as mock1:
        mock1.return_value.json.return_value = {"prices": []}
        r = getrate.getCoingeckoRate("OCEAN", "2022-01-20", "2022-01-20")

    assert r is None

    with pytest.raises(ValueError):
        with patch("df_py.util.getrate._coingeckoId") as mock1:
            mock1.return_value = ""
            r = getrate.getCoingeckoRate("OCEAN", "2022-01-20", "2022-01-20")

    with patch("df_py.util.getrate.json.load") as mock1:
        mock1.return_value = {}
        r = getrate._coingeckoId("OCEAN")

    assert r == ""
