import brownie
from enforce_typing import enforce_types
from pprint import pprint
import pytest
from util import query
from util.blockrange import BlockRange
from util.oceanutil import OCEAN_address, CONTRACTS, OCEANtoken, recordDeployedContracts
from util.test import conftest
from util.constants import BROWNIE_PROJECT as B
import time, random, string


accounts = brownie.network.accounts
chain = brownie.network.chain

CHAINID = 0

rndString = ''.join(random.sample(list(string.ascii_lowercase),5))
CO2 = B.Simpletoken.deploy(f"Carbon Dioxide {rndString}", f"CO2 ${rndString}", 18, 1e26, {"from": accounts[0]})

@enforce_types
def test_SimplePool():
    pool = query.SimplePool(
        "0xpool_addr", "0xnft_addr", "0xdt_addr", "DT", "0xbasetoken_addr")
    assert "SimplePool" in str(pool)


@enforce_types
def test_getPools(ADDRESS_FILE):
    _setup(ADDRESS_FILE)
    pools = query.getPools(CHAINID)
    assert pools


@enforce_types
def test_getStakes(ADDRESS_FILE):
    _setup(ADDRESS_FILE)
    _setup_co2(ADDRESS_FILE)
    st, fin, n = 1, len(chain), 50
    rng = BlockRange(st, fin, n)
    pools = query.getPools(CHAINID)
    stakes = query.getStakes(pools, rng, CHAINID)

    # OCEAN
    for stakes_at_pool in stakes["OCEAN"].values():
        assert len(stakes_at_pool) > 0
        assert min(stakes_at_pool.values()) > 0.0

    # CO2
    for stakes_at_pool in stakes[f"Carbon Dioxide {rndString}".upper()].values():
        assert len(stakes_at_pool) > 0
        assert min(stakes_at_pool.values()) > 0.0


@enforce_types
def test_getDTVolumes(ADDRESS_FILE):
    _setup(ADDRESS_FILE)
    st, fin = 1, len(chain)
    DT_vols = query.getDTVolumes(st, fin, CHAINID, OCEAN_address())
    assert sum(DT_vols.values()) > 0.0

@enforce_types
def test_getDTVolumes_CO2(ADDRESS_FILE):
    _setup_co2(ADDRESS_FILE)
    st, fin = 1, len(chain)
    DT_vols = query.getDTVolumes(st, fin, CHAINID, CO2.address)
    assert sum(DT_vols.values()) > 0.0



@enforce_types
def test_getPoolVolumes(ADDRESS_FILE):
    _setup(ADDRESS_FILE)
    pools = query.getPools(CHAINID)
    st, fin = 1, len(chain)
    poolvols = query.getPoolVolumes(pools, st, fin, CHAINID, OCEAN_address())
    assert poolvols
    assert sum(poolvols["OCEAN"].values()) > 0.0

@enforce_types
def test_getPoolVolumes_CO2(ADDRESS_FILE):
    _setup_co2(ADDRESS_FILE)
    pools = query.getPools(CHAINID)
    st, fin = 1, len(chain)
    poolvols = query.getPoolVolumes(pools, st, fin, CHAINID, CO2.address)
    assert poolvols
    assert sum(poolvols[f"Carbon Dioxide {rndString}".upper()].values()) > 0.0


@enforce_types
def test_getApprovedTokens(ADDRESS_FILE):
    _setup(ADDRESS_FILE)
    approved_tokens = query.getApprovedTokens(CHAINID)

    # OCEAN
    assert OCEAN_address().lower() in approved_tokens.keys()
    assert "OCEAN" in approved_tokens.values()

    # CO2
    assert CO2.address.lower() in approved_tokens.keys()
    assert f"Carbon Dioxide {rndString}".upper() in approved_tokens.values()


# ========================================================================
@enforce_types
def _setup(ADDRESS_FILE, num_pools=1):
    recordDeployedContracts(ADDRESS_FILE, CHAINID)
    conftest.fillAccountsWithOCEAN()
    conftest.randomDeployTokensAndPoolsThenConsume(num_pools, OCEANtoken())
    time.sleep(2)

added = False
@enforce_types
def _setup_co2(ADDRESS_FILE, num_pools=1):
    global added
    recordDeployedContracts(ADDRESS_FILE, CHAINID)
    if added == False:
        CONTRACTS["Router"].addApprovedToken(
            CO2.address,{"from":accounts[0]}
        )
        added = True
    conftest.fillAccountsWithToken(CO2)
    conftest.randomDeployTokensAndPoolsThenConsume(num_pools,CO2)
    time.sleep(2)
