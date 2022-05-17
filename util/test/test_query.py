import brownie
from enforce_typing import enforce_types
from pprint import pprint
import pytest
from util import chainlist, query
from util.blockrange import BlockRange
from util.oceanutil import OCEAN_address, OCEANtoken, recordDeployedContracts
from util.test import conftest
from util.constants import BROWNIE_PROJECT as B
import time, random, string

account0 = brownie.network.accounts[0]
chain = brownie.network.chain

CHAINID = 0

rndString = "".join(random.sample(list(string.ascii_uppercase),5))
CO2_SYM = f"CO2_{rndString.upper()}"
CO2 = B.Simpletoken.deploy(CO2_SYM, CO2_SYM, 18, 1e26, {"from": account0})


@enforce_types
def test_SimplePool():
    pool = query.SimplePool(
        "0xpool_addr", "0xnft_addr", "0xdt_addr", "DT", CO2.address)
    assert "SimplePool" in str(pool)


@enforce_types
def test_getPools_OCEAN():
    _test_getPools("OCEAN")


@enforce_types
def test_getPools_CO2():
    _test_getPools("CO2")


@enforce_types
def _test_getPools(base_token_str):
    base_token = _setup(base_token_str)
    pools = query.getPools(CHAINID)
    pools_with_token = [pool.basetoken_addr == base_token.address
                        for pool in pools]
    assert pools_with_token


@enforce_types
def test_getStakes_OCEAN():
    _test_getStakes("OCEAN")


@enforce_types
def test_getStakes_CO2():
    _test_getStakes("CO2")


@enforce_types
def _test_getStakes(base_token_str):
    base_token = _setup(base_token_str)
    st, fin, n = 1, len(chain), 250
    rng = BlockRange(st, fin, n)
    pools = query.getPools(CHAINID)
    stakes = query.getStakes(pools, rng, CHAINID)

    for stakes_at_pool in stakes[base_token.symbol().upper()].values():
        assert len(stakes_at_pool) > 0
        assert min(stakes_at_pool.values()) > 0.0


@enforce_types
def test_getDTVolumes_OCEAN():
    _tesT_getDTVolumes("OCEAN")


@enforce_types
def test_getDTVolumes_CO2():
    _tesT_getDTVolumes("CO2")


@enforce_types
def _test_getDTVolumes(base_token_str):
    base_token = _setup(base_token_str)
    st, fin = 1, len(chain)
    DT_vols = query.getDTVolumes(st, fin, CHAINID, base_token.address)
    assert sum(DT_vols.values()) > 0.0


@enforce_types
def test_getPoolVolumes_OCEAN():
    _test_getPoolVolumes("OCEAN")


@enforce_types
def test_getPoolVolumes_CO2():
    _test_getPoolVolumes("CO2")


@enforce_types
def _test_getPoolVolumes(base_token_str):
    base_token = _setup(base_token_str)
    pools = query.getPools(CHAINID)
    st, fin = 1, len(chain)
    poolvols = query.getPoolVolumes(pools, st, fin, CHAINID, base_token.address)
    assert poolvols
    assert sum(poolvols[base_token.symbol().upper()].values()) > 0.0


@enforce_types
def test_getApprovedTokens():
    _setup("OCEAN")
    _setup("CO2")
    approved_tokens = query.getApprovedTokens(CHAINID)

    # OCEAN - approved
    assert OCEAN_address().lower() in approved_tokens.keys()
    assert "OCEAN" in approved_tokens.values()

    # CO2 - not approved
    assert CO2.address.lower() not in approved_tokens.keys()
    assert _CO2_SYM in approved_tokens.values()


# ========================================================================
@enforce_types
def _setup(base_token_str:str, num_pools=1):
    assert base_token_str in ["OCEAN", "CO2"], "only testing OCEAN & CO2"
    
    ADDRESS_FILE = chainlist.chainIdToAddressFile(CHAINID)
    recordDeployedContracts(ADDRESS_FILE, CHAINID)
    
    base_token = OCEANtoken() if base_token_str == "OCEAN" else CO2
    conftest.fillAccountsWithToken(base_token)
    conftest.randomDeployTokensAndPoolsThenConsume(num_pools, base_token)
    time.sleep(2)
    
    return base_token
    
