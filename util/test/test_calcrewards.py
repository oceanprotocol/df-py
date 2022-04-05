from enforce_typing import enforce_types
import pytest

from util import calcrewards

@enforce_types
def test_calcRewards1():
    stakes = {'pool1': {'LP1':1.0}}
    pool_vols = {'pool1':1.0}
    rewards = calcrewards.calcRewards(stakes, pool_vols, OCEAN_avail=10.0)
    assert rewards == {'LP1':10.0}

@enforce_types
def test_calcRewards2():
    stakes = {'pool1': {'LP1':1.0, 'LP2':1.0}}
    pool_vols = {'pool1':1.0}
    rewards = calcrewards.calcRewards(stakes, pool_vols, OCEAN_avail=10.0)
    assert sum(rewards.values()) == pytest.approx(10.0, 0.01)
    assert rewards == {'LP1':5.0, 'LP2':5.0}
    
@enforce_types
def test_calcRewards3():
    stakes = {'pool1': {'LP1':1.0, 'LP2':1.0},
              'pool2': {'LP1':1.0, 'LP3':1.0}}
    pool_vols = {'pool1':1.0} #pool1 has volume, but not pool2
    rewards = calcrewards.calcRewards(stakes, pool_vols, OCEAN_avail=10.0)
    assert sum(rewards.values()) == pytest.approx(10.0, 0.01)
    assert min(rewards.values()) > 0, "shouldn't have entries with 0 rewards"
    assert rewards == {'LP1':5.0, 'LP2':5.0}

@enforce_types
def test_calcRewards4():
    stakes = {'pool1': {'LP1':1.0, 'LP2':1.0},
              'pool2': {'LP1':1.0, 'LP3':1.0}}
    pool_vols = {'pool1':1.0, 'pool2':1.0} #pool1 and 2 both have volume
    rewards = calcrewards.calcRewards(stakes, pool_vols, OCEAN_avail=10.0)
    assert sum(rewards.values()) == pytest.approx(10.0, 0.01)
    assert rewards == {'LP1':5.0, 'LP2':2.5, 'LP3':2.5}
