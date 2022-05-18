import brownie
from enforce_typing import enforce_types
from pprint import pprint
import random, time

from util import chainlist, query
from util.blockrange import BlockRange
from util.constants import BROWNIE_PROJECT as B
from util.oceanutil import OCEANtoken, recordDeployedContracts
from util.test import conftest

account0 = brownie.network.accounts[0]
chain = brownie.network.chain

CHAINID = 0
   

def test_all():
    """Run this all as a single test, because we may have to
    re-loop or sleep until the info we want is there."""

    address_file = chainlist.chainIdToAddressFile(CHAINID)
    recordDeployedContracts(address_file, CHAINID)
    
    OCEAN = OCEANtoken()
    conftest.fillAccountsWithToken(OCEAN)
        
    CO2_SYM = f"CO2_{random.randint(0,99999):05d}"
    CO2 = B.Simpletoken.deploy(
        CO2_SYM, CO2_SYM, 18, 1e26, {"from": account0})
    conftest.fillAccountsWithToken(CO2)

    #keep deploying, until TheGraph node sees volume, or timeout
    # (assumes that with volume, everything else is there too
    for loop_i in range(100):
        assert loop_i < 5, "timeout" 
        if _foundStakeAndConsume(CO2_SYM):
            break
        conftest.randomDeployTokensAndPoolsThenConsume(2, OCEAN)
        conftest.randomDeployTokensAndPoolsThenConsume(2, CO2)
        print(f"loop_i={loop_i}")
        time.sleep(2)

    #run actual tests
    _test_SimplePool(CO2)
    _test_getApprovedTokens(CO2_SYM)
    _test_pools(CO2_SYM)
    _test_stakes(CO2_SYM)
    _test_getDTVolumes(CO2_SYM)
    _test_getPoolVolumes(CO2_SYM)


def _foundStakeAndConsume(CO2_SYM):
    #nonzero CO2 stake?
    pools = query.getPools(CHAINID)
    st, fin, n = 1, len(chain), 250
    rng = BlockRange(st, fin, n)
    stakes_at_chain = query.getStakes(pools, rng, CHAINID)
    if CO2_SYM not in stakes_at_chain:
        return False
    for stakes_at_pool in stakes_at_chain[CO2_SYM].values():
        if not stakes_at_pool:
            return False
        lowest_stake = min(stakes_at_pool.values())
        if lowest_stake == 0:
            return False
    
    #nonzero CO2 volume?
    st, fin = 1, len(chain)
    DT_vols = query.getDTVolumes(st, fin, CHAINID)
    if CO2_SYM not in DT_vols:
        return False
    if sum(DT_vols[CO2_SYM].values()) == 0:
        return False

    #all good
    return True


@enforce_types
def _test_SimplePool(CO2):
    pool = query.SimplePool(
        "0xpool_addr", "0xnft_addr", "0xdt_addr", "DT", CO2.address)
    assert "SimplePool" in str(pool)


@enforce_types
def _test_getApprovedTokens(CO2_SYM:str):
    approved_tokens = query.getApprovedTokens(CHAINID)
    assert "OCEAN" in approved_tokens.values()
    assert CO2_SYM not in approved_tokens.values()

    
@enforce_types
def _test_pools(CO2_SYM:str):
    pools = query.getPools(CHAINID)
    assert [p for p in pools if p.basetoken_symbol == "OCEAN"]
    assert [p for p in pools if p.basetoken_symbol == CO2_SYM]


@enforce_types
def _test_stakes(CO2_SYM:str):
    pools = query.getPools(CHAINID)
    st, fin, n = 1, len(chain), 250
    rng = BlockRange(st, fin, n)
    stakes = query.getStakes(pools, rng, CHAINID)

    assert "OCEAN" in stakes, stakes.keys()
    assert CO2_SYM in stakes, (CO2_SYM, stakes.keys())
    
    for basetoken_symbol in ["OCEAN", CO2_SYM]:
        for stakes_at_pool in stakes[basetoken_symbol].values():
            assert len(stakes_at_pool) > 0
            assert min(stakes_at_pool.values()) > 0.0


@enforce_types
def _test_getDTVolumes(CO2_SYM:str):
    st, fin = 1, len(chain)
    DT_vols = query.getDTVolumes(st, fin, CHAINID)
    assert "OCEAN" in DT_vols, DT_vols.keys()
    assert CO2_SYM in DT_vols, (CO2_SYM, DT_vols.keys())
    assert sum(DT_vols["OCEAN"].values()) > 0.0
    assert sum(DT_vols[CO2_SYM].values()) > 0.0


@enforce_types
def _test_getPoolVolumes(CO2_SYM:str):
    pools = query.getPools(CHAINID)
    st, fin = 1, len(chain)
    poolvols = query.getPoolVolumes(pools, st, fin, CHAINID)
    assert "OCEAN" in poolvols, poolvols.keys()
    assert CO2_SYM in poolvols, (CO2_SYM, poolvols.keys())
    assert sum(poolvols["OCEAN"].values()) > 0.0
    assert sum(poolvols[CO2_SYM].values()) > 0.0
