import brownie
from enforce_typing import enforce_types
from pprint import pprint
import pytest

from util import query
from util.blockrange import BlockRange
from util.oceanutil import OCEAN_address, recordDeployedContracts
from util.test import conftest

accounts = brownie.network.accounts
chain = brownie.network.chain

CHAINID = 0

@enforce_types
def test_getPools(ADDRESS_FILE):
    _setup(ADDRESS_FILE)
    pools = query.getPools(CHAINID)
    assert pools


@enforce_types
def test_getStakes(ADDRESS_FILE):
    _setup(ADDRESS_FILE)
    st, fin, n = 1, len(chain), 50
    rng = BlockRange(st, fin, n)
    pools = query.getPools(CHAINID)
    stakes = query.getStakes(pools, rng, CHAINID)

    for stakes_at_pool in stakes["ocean"].values():
        assert len(stakes_at_pool) > 0
        assert min(stakes_at_pool.values()) > 0.0


@enforce_types
def test_getDTVolumes(ADDRESS_FILE):
    _setup(ADDRESS_FILE)
    st, fin = 1, len(chain)
    DT_vols = query.getDTVolumes(st, fin, CHAINID)
    assert sum(DT_vols.values()) > 0.0


@enforce_types
def test_getPoolVolumes(ADDRESS_FILE):
    _setup(ADDRESS_FILE)
    pools = query.getPools(CHAINID)
    st, fin = 1, len(chain)
    poolvols = query.getPoolVolumes(pools, st, fin, CHAINID)
    assert poolvols
    assert sum(poolvols["ocean"].values()) > 0.0


@enforce_types
def test_getApprovedTokens(ADDRESS_FILE):
    _setup(ADDRESS_FILE)
    approved_tokens = query.getApprovedTokens(CHAINID)
    assert OCEAN_address().lower() in approved_tokens.keys()
    assert "ocean" in approved_tokens.values()


# ========================================================================
@enforce_types
def _setup(ADDRESS_FILE, num_pools=1):
    recordDeployedContracts(ADDRESS_FILE, CHAINID)
    conftest.fillAccountsWithOCEAN()
    conftest.randomDeployTokensAndPoolsThenConsume(num_pools)
