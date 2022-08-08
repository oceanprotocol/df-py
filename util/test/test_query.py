import random
import time

import pytest
import brownie
from enforce_typing import enforce_types

from util import oceanutil, oceantestutil, networkutil, query
from util.blockrange import BlockRange
from util.constants import BROWNIE_PROJECT as B, CONTRACTS

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
    fre_tup = []
    for loop_i in range(1):
        print(f"loop {loop_i} start")
        assert loop_i < 5, "timeout"
        # if _foundStakeAndConsume(CO2_ADDR):
        #     break

        new_fre = oceantestutil.randomCreateDataNFTWithFREs(2, OCEAN)

        print("fre_tup before: ", fre_tup)
        fre_tup = fre_tup + new_fre
        print("fre_tup after: ", fre_tup)

        oceantestutil.randomLockAndAllocate(fre_tup)
        oceantestutil.randomConsumeFREs(fre_tup, oceanutil.OCEANtoken())

        print(f"loop {loop_i} not successful, so sleep and re-loop")
        time.sleep(2)

    # run actual tests
    # _test_SimplePool(CO2)
    # _test_getApprovedTokens()
    # _test_getSymbols()
    # _test_pools(CO2_ADDR)
    # _test_stakes(CO2_ADDR)
    # _test_getDTVolumes(CO2_ADDR)
    # _test_getPoolVolumes(CO2_ADDR)
    # _test_query(CO2_ADDR)


def _foundStakeAndConsume(CO2_ADDR):
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
def _test_getApprovedTokens():
    approved_tokens = query.getApprovedTokens(CHAINID)
    assert approved_tokens.hasSymbol(CHAINID, "OCEAN")


@enforce_types
def _test_getSymbols():
    approved_tokens = query.getApprovedTokens(CHAINID)
    symbols_at_chain = query.getSymbols(
        approved_tokens, CHAINID
    )  # dict of [basetoken_addr] : basetoken_symbol

    OCEAN_tok = approved_tokens.tokAtSymbol(CHAINID, "OCEAN")
    assert symbols_at_chain[OCEAN_tok.address] == "OCEAN"


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
def test_shares_to_stakes():
    share = 10.0
    pool_liq = 300.0
    total_shares = 100.0
    assert query.poolSharestoValue(share, total_shares, pool_liq) == 30.0


@enforce_types
def test_stakes_shares_conversion():
    ocean = oceanutil.OCEANtoken()
    account1 = brownie.network.accounts[1]
    (DT, pool) = oceantestutil.deployPool(100.0, 1.0, account0, ocean)
    oceantestutil.addStake(pool, 10.0, account1, ocean)
    oceantestutil.buyDT(pool, DT, 10.0, 100.0, account0, ocean)
    oceantestutil.buyDT(pool, DT, 10.0, 100.0, account0, ocean)
    oceantestutil.buyDT(pool, DT, 10.0, 100.0, account0, ocean)
    oceantestutil.buyDT(pool, DT, 10.0, 100.0, account0, ocean)
    oceantestutil.buyDT(pool, DT, 10.0, 100.0, account0, ocean)
    time.sleep(2)
    now = len(brownie.network.chain)
    rng = BlockRange(now - 1, now, 1)
    for _ in range(50):
        try:
            stakes = query.getStakes([], rng, CHAINID)
            stakes = stakes[ocean.address.lower()][pool.address.lower()]
            break
        # pylint: disable=bare-except
        except:
            time.sleep(2)
            brownie.network.chain.mine(blocks=5)
    ocn_balance = ocean.balanceOf(pool.address)
    tot_sup = pool.totalSupply()
    final = pool.balanceOf(account1) / tot_sup * ocn_balance
    assert pool.balanceOf(account1) / 1e18 == 5.0  # shares
    assert stakes[account1.address.lower()] == pytest.approx(final / 1e18, 0.1)


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
    (__, S0, V0, A0, SYM0) = query.query_all(rng, CHAINID)

    # tests are light here, as we've tested piecewise elsewhere
    assert CO2_ADDR in S0
    assert CO2_ADDR in V0
    assert A0
    assert SYM0


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
