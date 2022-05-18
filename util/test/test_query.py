import brownie
from enforce_typing import enforce_types
from pprint import pprint
import random

from util import chainlist, query
from util.blockrange import BlockRange
from util.constants import BROWNIE_PROJECT as B
from util.oceanutil import OCEANtoken, recordDeployedContracts
from util.test import conftest

account0 = brownie.network.accounts[0]
chain = brownie.network.chain

CHAINID = 0

OCEAN = None
CO2, CO2_SYM = None

@enforce_types
def test_SimplePool():
    pool = query.SimplePool(
        "0xpool_addr", "0xnft_addr", "0xdt_addr", "DT", CO2.address)
    assert "SimplePool" in str(pool)


@enforce_types
def test_getPools():
    assert _poolsHaveToken("OCEAN")
    assert _poolsHaveToken(CO2_SYM)


@enforce_types
def test_getStakes():
    st, fin, n = 1, len(chain), 250
    rng = BlockRange(st, fin, n)
    pools = query.getPools(CHAINID)
    stakes = query.getStakes(pools, rng, CHAINID)

    for basetoken_symbol in ["OCEAN", CO2_SYM]:
        assert basetoken_symbol in stakes
        for stakes_at_pool in stakes[basetoken_symbol].values():
            assert len(stakes_at_pool) > 0
            assert min(stakes_at_pool.values()) > 0.0


@enforce_types
def test_getDTVolumes():
    st, fin = 1, len(chain)
    DT_vols = query.getDTVolumes(st, fin, CHAINID)
    assert sum(DT_vols["OCEAN"].values()) > 0.0
    assert sum(DT_vols[CO2_SYM].values()) > 0.0


@enforce_types
def test_getPoolVolumes():
    pools = query.getPools(CHAINID)
    st, fin = 1, len(chain)
    poolvols = query.getPoolVolumes(pools, st, fin, CHAINID)
    assert sum(poolvols["OCEAN"].values()) > 0.0
    assert sum(poolvols[CO2_SYM].values()) > 0.0


@enforce_types
def test_getApprovedTokens():
    approved_tokens = query.getApprovedTokens(CHAINID)
    assert "OCEAN" in approved_tokens.values()
    assert CO2_SYM not in approved_tokens.values()
    

# ========================================================================
@enforce_types
def setup_module():
    """Runs before each test"""

    address_file = chainlist.chainIdToAddressFile(CHAINID)
    recordDeployedContracts(address_file, CHAINID)
    
    global OCEAN
    if OCEAN is None:
        OCEAN = OCEANtoken()
        conftest.fillAccountsWithToken(OCEAN)
        
    global CO2, CO2_SYM
    if CO2 is None:
        CO2_SYM = f"CO2_{random.randint(0,99999):05d}"
        CO2 = B.Simpletoken.deploy(
            CO2_SYM, CO2_SYM, 18, 1e26, {"from": account0})
        conftest.fillAccountsWithToken(CO2)
        
    _randomDeployUntilHaveTokenOrTimeout("OCEAN")
    _randomDeployUntilHaveTokenOrTimeout(CO2_SYM)


def _deployEtcUntilHaveTokenOrTimeout(symbol:str):
    for loop_i in range(10):
        if _poolsHaveToken(symbol):
            break
        conftest.randomDeployTokensAndPoolsThenConsume(2, symbol)
        time.sleep(2)


def _poolsHaveToken(symbol:str) -> bool:
    pools = query.getPools(CHAINID)
    return bool([pool for pool in pools
                 if p.basetoken_symbol == "OCEAN" for p in pools])
