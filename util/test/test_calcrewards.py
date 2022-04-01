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
    rewards = calcrewards.calcRewards(rng, OCEAN_avail, SUBGRAPH_URL)
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

#========================================================================
@enforce_types
def _setup(ADDRESS_FILE, SUBGRAPH_URL, num_pools=1):
    recordDeployedContracts(ADDRESS_FILE, "development")
    conftest.fillAccountsWithOCEAN()
    conftest.randomDeployTokensAndPoolsThenConsume(num_pools)
