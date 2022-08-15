import random
import time

import pytest
import brownie
from enforce_typing import enforce_types
from pytest import approx

from util import oceanutil, oceantestutil, networkutil, query
from util.base18 import toBase18
from util.blockrange import BlockRange
from util.constants import BROWNIE_PROJECT as B

account0, QUERY_ST = None, 0

CHAINID = networkutil.DEV_CHAINID
OCEAN_ADDR: str = ""
WEEK = 7 * 86400


# Test flow.
# Create veOCEAN locks
# Create data NFTs and consume.
# Allocate veOCEAN for the data NFTs.
# Query veOCEAN balances, allocations, and volumes.
# Calculate and compare the results with the expected values.


@pytest.mark.timeout(300)
def test_all():
    """Run this all as a single test, because we may have to
    re-loop or sleep until the info we want is there."""

    startBlockNumber = len(brownie.network.chain)
    endBlockNumber = 0  # will be set later

    CO2_SYM = f"CO2_{random.randint(0,99999):05d}"
    CO2 = B.Simpletoken.deploy(CO2_SYM, CO2_SYM, 18, 1e26, {"from": account0})
    CO2_ADDR = CO2.address.lower()
    OCEAN = oceanutil.OCEANtoken()
    oceantestutil.fillAccountsWithToken(CO2)
    accounts = []
    publisher_account = account0
    OCEAN_LOCK_AMT = toBase18(5.0)
    for i in range(5):
        accounts.append(brownie.network.accounts.add())
        CO2.transfer(accounts[i], toBase18(11000.0), {"from": account0})
        OCEAN.transfer(accounts[i], OCEAN_LOCK_AMT, {"from": account0})

    # Create data nfts
    dataNfts = []
    for i in range(5):
        (data_NFT, DT, exchangeId) = oceanutil.createDataNFTWithFRE(
            publisher_account, CO2
        )
        assert oceanutil.FixedPrice().isActive(exchangeId) is True
        dataNfts.append((data_NFT, DT, exchangeId))

    # Lock veOCEAN
    t0 = brownie.network.chain.time()
    t1 = t0 // WEEK * WEEK + WEEK
    t2 = t1 + WEEK * 20  # lock for 20 weeks
    brownie.network.chain.sleep(t1 - t0)
    for i in range(5):
        oceanutil.create_ve_lock(OCEAN_LOCK_AMT, t2, accounts[i])

    # Allocate to data NFTs
    for i in range(5):
        oceanutil.set_allocation(
            100,
            dataNfts[i][0],
            8996,
            accounts[i],
        )

    # Consume
    for i in range(5):
        oceantestutil.buyDTFRE(dataNfts[i][2], 1.0, 10000.0, accounts[i], CO2)
        oceantestutil.consumeDT(dataNfts[i][1], publisher_account, accounts[i])

    # keep deploying, until TheGraph node sees volume, or timeout
    # (assumes that with volume, everything else is there too
    for loop_i in range(50):
        endBlockNumber = len(brownie.network.chain)
        print(f"loop {loop_i} start")
        assert loop_i < 5, "timeout"
        if _foundConsume(CO2_ADDR, startBlockNumber, endBlockNumber):
            break
        brownie.network.chain.sleep(10)
        brownie.network.chain.mine(10)
        time.sleep(2)

    brownie.network.chain.sleep(10)
    brownie.network.chain.mine(20)

    time.sleep(2)

    blockRange = BlockRange(startBlockNumber, endBlockNumber, 100, 42)

    # run actual tests
    _test_getApprovedTokens()
    _test_getSymbols()
    _test_getDTVolumes(CO2_ADDR, startBlockNumber, endBlockNumber)
    _test_getveBalances(blockRange)
    _test_getAllocations(blockRange)
    # _test_query(CO2_ADDR)


def _foundConsume(CO2_ADDR, st, fin):
    DT_vols = query.getDTVolumes(st, fin, CHAINID)
    if CO2_ADDR not in DT_vols:
        return False
    if sum(DT_vols[CO2_ADDR].values()) == 0:
        return False

    # all good
    return True


@enforce_types
def _test_getveBalances(rng: BlockRange):
    veBalances = query.getveBalances(rng, CHAINID)
    assert len(veBalances) > 0
    assert sum(veBalances.values()) > 0

    for account in veBalances:
        bal = oceanutil.get_ve_balance(account) / 1e18
        assert veBalances[account] == approx(bal, 0.001)


@enforce_types
def _test_getAllocations(rng: BlockRange):
    allocations = query.getAllocations(rng, CHAINID)

    assert len(allocations) > 0

    for chainId in allocations:
        for nftAddr in allocations[chainId]:
            for userAddr in allocations[chainId][nftAddr]:
                totalAllocation = oceanutil.veAllocate().getTotalAllocation(userAddr)
                allocation = oceanutil.veAllocate().getveAllocation(
                    userAddr, nftAddr, chainId
                )
                assert (
                    allocations[chainId][nftAddr][userAddr]
                    == allocation / totalAllocation
                )


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
def _test_getDTVolumes(CO2_ADDR: str, st, fin):
    DT_vols = query.getDTVolumes(st, fin, CHAINID)
    assert CO2_ADDR in DT_vols, (CO2_ADDR, DT_vols.keys())
    assert sum(DT_vols[CO2_ADDR].values()) > 0.0


@enforce_types
def _test_query(CO2_ADDR: str):
    st, fin, n = QUERY_ST, len(brownie.network.chain), 500
    rng = BlockRange(st, fin, n)
    (V0, A0, SYM0) = query.query_all(rng, CHAINID)

    # tests are light here, as we've tested piecewise elsewhere
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
