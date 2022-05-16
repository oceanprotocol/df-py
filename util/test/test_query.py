from time import time
import brownie
from enforce_typing import enforce_types
from pprint import pprint
import pytest
from util import query
from util.blockrange import BlockRange
from util.oceanutil import OCEAN_address, recordDeployedContracts
from util.test import conftest
import time

accounts = brownie.network.accounts
chain = brownie.network.chain


@enforce_types
def test_getPools(ADDRESS_FILE, SUBGRAPH_URL):
    _setup(ADDRESS_FILE, SUBGRAPH_URL)
    pools = query.getPools(SUBGRAPH_URL)
    assert pools


@enforce_types
def test_getStakes(ADDRESS_FILE, SUBGRAPH_URL):
    _setup(ADDRESS_FILE, SUBGRAPH_URL)
    st, fin, n = 1, len(chain), 50
    rng = BlockRange(st, fin, n)
    pools = query.getPools(SUBGRAPH_URL)
    stakes = query.getStakes(pools, rng, SUBGRAPH_URL)

    for stakes_at_pool in stakes["ocean"].values():
        assert len(stakes_at_pool) > 0
        assert min(stakes_at_pool.values()) > 0.0


@enforce_types
def test_getDTVolumes(ADDRESS_FILE, SUBGRAPH_URL):
    _setup(ADDRESS_FILE, SUBGRAPH_URL)
    st, fin = 1, len(chain)
    DT_vols = query.getDTVolumes(st, fin, SUBGRAPH_URL)
    assert sum(DT_vols.values()) > 0.0


@enforce_types
def test_getPoolVolumes(ADDRESS_FILE, SUBGRAPH_URL):
    _setup(ADDRESS_FILE, SUBGRAPH_URL)
    pools = query.getPools(SUBGRAPH_URL)
    st, fin = 1, len(chain)
    poolvols = query.getPoolVolumes(pools, st, fin, SUBGRAPH_URL)
    assert poolvols
    assert sum(poolvols["ocean"].values()) > 0.0


@enforce_types
def test_getApprovedTokens(ADDRESS_FILE, SUBGRAPH_URL):
    _setup(ADDRESS_FILE, SUBGRAPH_URL)
    approved_tokens = query.getApprovedTokens(SUBGRAPH_URL)
    assert OCEAN_address().lower() in approved_tokens.keys()
    assert "ocean" in approved_tokens.values()


# ========================================================================
@enforce_types
def _setup(ADDRESS_FILE, SUBGRAPH_URL, num_pools=1):
    recordDeployedContracts(ADDRESS_FILE, "development")
    conftest.fillAccountsWithOCEAN()
    conftest.randomDeployTokensAndPoolsThenConsume(num_pools)
    time.sleep(2)
