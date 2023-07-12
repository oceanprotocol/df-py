from unittest.mock import patch

import pytest
from enforce_typing import enforce_types
from pytest import approx

from df_py.util import get_rate


@enforce_types
def test_get_binance_rate_OCEAN_sameday():
    r = get_rate.get_binance_rate("OCEAN", "2022-01-20", "2022-01-20")
    assert r == approx(0.75, 0.1)

@enforce_types
def test_get_binance_5m_tusd():
    interval = '5m'
    start_time = '2023-05-02_00:05'
    end_time = '2023-05-02_01:00'
    r = get_rate.get_binance_rate("BTC", start_time, end_time, "TUSD", interval)
    assert r == 27975.8475

    r = get_rate.get_binance_rate_all("BTC", start_time, end_time, "TUSD", interval)
    assert r == 27975.8475
@enforce_types
def test_get_coingecko_rate_OCEAN_sameday():
    r = get_rate.get_coingecko_rate("OCEAN", "2022-01-20", "2022-01-20")
    assert r == approx(0.75, 0.1)


@enforce_types
def test_get_rate_OCEAN_sameday():
    r = get_rate.get_rate("OCEAN", "2022-01-20", "2022-01-20")
    assert r == approx(0.75, 0.1)


@enforce_types
def test_get_rate_OCEAN_oneweek():
    r = get_rate.get_rate("OCEAN", "2022-01-20", "2022-01-26")
    assert r == approx(0.65, 0.1)


@enforce_types
def test_get_rate_H2O():
    r = get_rate.get_rate("H2O", "2022-05-13", "2022-05-25")
    assert r == approx(1.50, 0.1)

    # special case in coingecko
    r = get_rate.get_coingecko_rate("H2O", "2022-05-13", "2022-05-25")
    assert r == 1.618


@enforce_types
def test_get_rate_fallback():
    with patch("df_py.util.get_rate.get_binance_rate") as mock1:
        mock1.return_value = None
        r = get_rate.get_rate("OCEAN", "2022-01-20", "2022-01-20")

    # from goingecko
    assert r == approx(0.75, 0.1)

    with patch("df_py.util.get_rate.get_binance_rate") as mock1:
        mock1.return_value = None
        with patch("df_py.util.get_rate.get_coingecko_rate") as mock2:
            mock2.return_value = None
            r = get_rate.get_rate("OCEAN", "2022-01-20", "2022-01-20")

    assert r is None


@enforce_types
def test_get_rate_BTC():
    r = get_rate.get_rate("BTC", "2022-01-31", "2022-01-31")
    assert r == approx(37983.15, 0.1)


@enforce_types
def test_start_after_fin():
    p = get_rate.get_rate("OCEAN", "2021-01-26", "2021-12-20")
    assert p == approx(0.89, 0.1)


@enforce_types
def test_get_binance_rate_empty():
    with patch("df_py.util.get_rate.requests.get") as mock1:
        mock1.return_value.json.return_value = {}
        r = get_rate.get_binance_rate("OCEAN", "2022-01-20", "2022-01-20")

    assert r is None

    with patch("df_py.util.get_rate.requests.get") as mock1:
        mock1.side_effect = Exception("test")
        r = get_rate.get_binance_rate("OCEAN", "2022-01-20", "2022-01-20")

    assert r is None


@enforce_types
def test_get_coingecko_rate_empty():
    with patch("df_py.util.get_rate.requests.get") as mock1:
        mock1.return_value.json.return_value = {}
        r = get_rate.get_coingecko_rate("OCEAN", "2022-01-20", "2022-01-20")

    assert r is None

    with patch("df_py.util.get_rate.requests.get") as mock1:
        mock1.return_value.json.return_value = {"prices": []}
        r = get_rate.get_coingecko_rate("OCEAN", "2022-01-20", "2022-01-20")

    assert r is None

    with pytest.raises(ValueError):
        with patch("df_py.util.get_rate._coingecko_id") as mock1:
            mock1.return_value = ""
            r = get_rate.get_coingecko_rate("OCEAN", "2022-01-20", "2022-01-20")

    with patch("df_py.util.get_rate.json.load") as mock1:
        mock1.return_value = {}
        r = get_rate._coingecko_id("OCEAN")

    assert r == ""
