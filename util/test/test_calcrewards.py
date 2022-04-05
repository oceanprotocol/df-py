import brownie
from enforce_typing import enforce_types
from pprint import pprint
import pytest

from util import calcrewards 
from util.blockrange import BlockRange
from util.oceanutil import recordDeployedContracts
from util.test import conftest

accounts = brownie.network.accounts
chain = brownie.network.chain

@enforce_types
def test_main(ADDRESS_FILE, SUBGRAPH_URL):
    _setup(ADDRESS_FILE, SUBGRAPH_URL, num_pools=2)
    st, fin, n = 1, len(chain), 5
    rng = BlockRange(st, fin, n)
    OCEAN_avail = 10000.0
    rewards = calcrewards.queryAndCalcRewards(rng, OCEAN_avail, SUBGRAPH_URL)
    sum_ = sum(rewards.values())
    assert sum_ == pytest.approx(OCEAN_avail, 0.01), sum_
    
@enforce_types
def test_getPools(ADDRESS_FILE, SUBGRAPH_URL):
    _setup(ADDRESS_FILE, SUBGRAPH_URL)
    pools = calcrewards.getPools(SUBGRAPH_URL)
    assert pools

@enforce_types
def test_getStakes(ADDRESS_FILE, SUBGRAPH_URL):
    _setup(ADDRESS_FILE, SUBGRAPH_URL)
    st, fin, n = 1, len(chain), 50
    rng = BlockRange(st, fin, n)
    pools = calcrewards.getPools(SUBGRAPH_URL)
    stakes = calcrewards.getStakes(pools, rng, SUBGRAPH_URL)

    assert len(stakes) > 0
    for stakes_at_pool in stakes.values():
        assert len(stakes_at_pool) > 0
        assert min(stakes_at_pool.values()) > 0.0
    
@enforce_types
def test_getDTVolumes(ADDRESS_FILE, SUBGRAPH_URL):
    _setup(ADDRESS_FILE, SUBGRAPH_URL)
    st, fin = 1, len(chain)
    DT_vols = calcrewards.getDTVolumes(st, fin, SUBGRAPH_URL)
    assert sum(DT_vols.values()) > 0.0

@enforce_types
def test_getPoolVolumes(ADDRESS_FILE, SUBGRAPH_URL):
    _setup(ADDRESS_FILE, SUBGRAPH_URL)
    pools = calcrewards.getPools(SUBGRAPH_URL)
    st, fin = 1, len(chain)
    pool_vols = calcrewards.getPoolVolumes(pools, st, fin, SUBGRAPH_URL)
    assert pool_vols
    assert sum(pool_vols.values()) > 0.0

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


#========================================================================
@enforce_types
def _setup(ADDRESS_FILE, SUBGRAPH_URL, num_pools=1):
    recordDeployedContracts(ADDRESS_FILE, "development")
    conftest.fillAccountsWithOCEAN()
    conftest.randomDeployTokensAndPoolsThenConsume(num_pools)
