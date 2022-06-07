import random
import time

import pytest
import brownie
from enforce_typing import enforce_types

from util import oceanutil, oceantestutil, networkutil, query
from util.blockrange import BlockRange
from util.constants import BROWNIE_PROJECT as B

account0, QUERY_ST = None, 0

CHAINID = networkutil.DEV_CHAINID
OCEAN_ADDR: str = ""


@pytest.mark.timeout(300)
def test_all():
    """Run this all as a single test, because we may have to
    re-loop or sleep until the info we want is there."""

    OCEAN = oceanutil.OCEANtoken()
    oceantestutil.fillAccountsWithToken(OCEAN)

    CO2_SYM = f"CO2_{random.randint(0,99999):05d}"
    CO2 = B.Simpletoken.deploy(CO2_SYM, CO2_SYM, 18, 1e26, {"from": account0})
    CO2_ADDR = CO2.address.lower()
    oceantestutil.fillAccountsWithToken(CO2)

    # keep deploying, until TheGraph node sees volume, or timeout
    # (assumes that with volume, everything else is there too
    for loop_i in range(100):
        print(f"loop {loop_i} start")
        assert loop_i < 5, "timeout"
        if _foundStakeAndConsume(CO2_ADDR):
            break
        oceantestutil.randomDeployTokensAndPoolsThenConsume(2, OCEAN)
        oceantestutil.randomDeployTokensAndPoolsThenConsume(2, CO2)
        print(f"loop {loop_i} not successful, so sleep and re-loop")
        time.sleep(2)

    # run actual tests
    _test_SimplePool(CO2)
    _test_getApprovedTokens(CO2_SYM)
    _test_pools(CO2_ADDR)
    _test_stakes(CO2_ADDR)
    _test_getDTVolumes(CO2_ADDR)
    _test_getPoolVolumes(CO2_ADDR)
    _test_query(CO2_ADDR)


def _foundStakeAndConsume(CO2_ADDR):
    # nonzero CO2 stake?
    pools = query.getPools(CHAINID)
    st, fin, n = QUERY_ST, len(brownie.network.chain), 20
    rng = BlockRange(st, fin, n)
    stakes_at_chain = query.getStakes(pools, rng, CHAINID)
    if CO2_ADDR not in stakes_at_chain:
        return False
    for stakes_at_pool in stakes_at_chain[CO2_ADDR].values():
        if not stakes_at_pool:
            return False
        lowest_stake = min(stakes_at_pool.values())
        if lowest_stake == 0:
            return False

    # nonzero CO2 volume?
    st, fin = QUERY_ST, len(brownie.network.chain)
    DT_vols = query.getDTVolumes(st, fin, CHAINID)
    if CO2_ADDR not in DT_vols:
        return False
    if sum(DT_vols[CO2_ADDR].values()) == 0:
        return False

    # all good
    return True


@enforce_types
def _test_SimplePool(CO2):
    pool = query.SimplePool("0xpool_addr", "0xnft_addr", "0xdt_addr", "DT", CO2.address)
    assert "SimplePool" in str(pool)


@enforce_types
def _test_getApprovedTokens(CO2_SYM: str):
    approved_tokens = query.getApprovedTokens(CHAINID)
    assert "OCEAN" in approved_tokens.values()
    assert CO2_SYM not in approved_tokens.values()


@enforce_types
def _test_pools(CO2_ADDR: str):
    pools = query.getPools(CHAINID)
    assert [p for p in pools if p.basetoken_addr == OCEAN_ADDR]
    assert [p for p in pools if p.basetoken_addr == CO2_ADDR]


@enforce_types
def _test_stakes(CO2_ADDR: str):
    pools = query.getPools(CHAINID)
    st, fin, n = QUERY_ST, len(brownie.network.chain), 500
    rng = BlockRange(st, fin, n)
    stakes = query.getStakes(pools, rng, CHAINID)

    assert OCEAN_ADDR in stakes, stakes.keys()
    assert CO2_ADDR in stakes, (CO2_ADDR, stakes.keys())

    for basetoken_address in [OCEAN_ADDR, CO2_ADDR]:
        for stakes_at_pool in stakes[basetoken_address].values():
            assert len(stakes_at_pool) > 0
            assert min(stakes_at_pool.values()) > 0.0


@enforce_types
def _test_getDTVolumes(CO2_ADDR: str):
    st, fin = QUERY_ST, len(brownie.network.chain)
    DT_vols = query.getDTVolumes(st, fin, CHAINID)
    assert OCEAN_ADDR in DT_vols, DT_vols.keys()
    assert CO2_ADDR in DT_vols, (CO2_ADDR, DT_vols.keys())
    assert sum(DT_vols[OCEAN_ADDR].values()) > 0.0
    assert sum(DT_vols[CO2_ADDR].values()) > 0.0


@enforce_types
def _test_getPoolVolumes(CO2_ADDR: str):
    pools = query.getPools(CHAINID)
    st, fin = QUERY_ST, len(brownie.network.chain)
    poolvols = query.getPoolVolumes(pools, st, fin, CHAINID)
    assert OCEAN_ADDR in poolvols, poolvols.keys()
    assert CO2_ADDR in poolvols, (CO2_ADDR, poolvols.keys())
    assert sum(poolvols[OCEAN_ADDR].values()) > 0.0
    assert sum(poolvols[CO2_ADDR].values()) > 0.0


@enforce_types
def _test_query(CO2_ADDR: str):
    st, fin, n = QUERY_ST, len(brownie.network.chain), 500
    rng = BlockRange(st, fin, n)
    (_, S0, V0) = query.query_all(rng, CHAINID)

    # tests are light here, as we've tested piecewise elsewhere
    assert CO2_ADDR in S0
    assert CO2_ADDR in V0


@enforce_types
def test_symbol():
    testToken = B.Simpletoken.deploy("CO2", "", 18, 1e26, {"from": account0})
    assert query.symbol(testToken) == "CO2"

    testToken = B.Simpletoken.deploy("ASDASDASD", "", 18, 1e26, {"from": account0})
    assert query.symbol(testToken) == "ASDASDASD"

    testToken = B.Simpletoken.deploy(
        "!@#$@!%$#^%$&~!@", "", 18, 1e26, {"from": account0}
    )
    assert query.symbol(testToken) == "!@#$@!%$#^%$&~!@"


@enforce_types
def setup_function():
    global OCEAN_ADDR

    networkutil.connect(networkutil.DEV_CHAINID)
    global account0, QUERY_ST
    account0 = brownie.network.accounts[0]
    QUERY_ST = max(0, len(brownie.network.chain) - 200)
    oceanutil.recordDevDeployedContracts()
    OCEAN_ADDR = oceanutil.OCEAN_address().lower()


@enforce_types
def teardown_function():
    networkutil.disconnect()
