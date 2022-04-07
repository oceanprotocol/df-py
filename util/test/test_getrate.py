import pytest
from pytest import approx

from util import getrate

def test_getrate_ocean_oneday():
    r = getrate.getrate("OCEAN", "2022-01-20", "2022-01-20")
    assert r == approx(0.75, 0.1) #coingecko numbers
    
def test_getrate_ocean_oneweek():
    r = getrate.getrate("OCEAN", "2022-01-20", "2022-01-26")
    assert r == approx(0.65, 0.1) #coingecko numbers
    
def test_getrate_h2o():
    for symbol in ["H2O", "H2o", "h2o"]:
        assert getrate.getrate(symbol, "foo", "bar") == approx(1.618, 0.1)

def test_start_after_fin():
    with pytest.raises(ValueError):
        getrate.getrate("OCEAN", "2021-01-26", "2021-12-20")
        
def test_ratelimit():
    with pytest.raises(ValueError):
        getrate.getrate("OCEAN", "2021-01-20", "2021-12-26")
        
def test_coingeckoRate_bitcoin():
    r = getrate.coingeckoRate("bitcoin", "2022-01-31")
    assert r == approx(37983.15, 0.1)

def test_coingeckoRate_ocean():
    r = getrate.coingeckoRate("ocean-protocol", "2022-01-31")
    assert r == approx(0.58, 0.1)
