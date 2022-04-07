from enforce_typing import enforce_types
import pytest

from util.calcrewards import calcRewards, _convertToUSD

RATES = {"ocean":0.5, "h2o":1.6}

@enforce_types
def test_calcRewards1():
    stakes = {"ocean": {"pool1": {"LP1":1.0}}}
    pool_vols = {"ocean": {"pool1":1.0}}
    rewards = calcRewards(stakes, pool_vols, RATES, OCEAN_avail=10.0)
    assert rewards == {"LP1":10.0}

@enforce_types
def test_calcRewards2():
    stakes = {"ocean": {"pool1": {"LP1":1.0, "LP2":1.0}}}
    pool_vols = {"ocean": {"pool1":1.0}}
    rewards = calcRewards(stakes, pool_vols, RATES, OCEAN_avail=10.0)
    assert sum(rewards.values()) == pytest.approx(10.0, 0.01)
    assert rewards == {"LP1":5.0, "LP2":5.0}
    
@enforce_types
def test_calcRewards3():
    stakes = {"ocean": {"pool1": {"LP1":1.0, "LP2":1.0},
                        "pool2": {"LP1":1.0, "LP3":1.0}}}
    pool_vols = {"pool1":1.0} #pool1 has volume, but not pool2
    rewards = calcRewards(stakes, pool_vols, RATES, OCEAN_avail=10.0)
    assert sum(rewards.values()) == pytest.approx(10.0, 0.01)
    assert min(rewards.values()) > 0, "shouldn't have entries with 0 rewards"
    assert rewards == {"LP1":5.0, "LP2":5.0}

@enforce_types
def test_calcRewards4():
    stakes = {"ocean": {"pool1": {"LP1":1.0, "LP2":1.0},
                        "pool2": {"LP1":1.0, "LP3":1.0}}}
    pool_vols = {"pool1":1.0, "pool2":1.0} #pool1 and 2 both have volume
    rewards = calcRewards(stakes, pool_vols, RATES, OCEAN_avail=10.0)
    assert sum(rewards.values()) == pytest.approx(10.0, 0.01)
    assert rewards == {"LP1":5.0, "LP2":2.5, "LP3":2.5}

@enforce_types
def test_convertToUSD1():
    stakes = {"ocean": {"pool1": {"LP1":3.0}}}
    pool_vols = {"ocean": {"pool1":9.0}}
    (stakes_USD, pool_vols_USD) = _convertToUSD(stakes, pool_vols, RATES)
    assert stakes_USD == {"pool1": {"LP1":3.0*0.5}}
    assert pool_vols_USD == {"pool1":9.0*0.5}
