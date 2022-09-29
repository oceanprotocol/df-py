import random
import time

import pytest
import brownie
from enforce_typing import enforce_types
from pytest import approx

from util import oceanutil, oceantestutil, networkutil, query
from util.base18 import toBase18
from util.blockrange import BlockRange
from util.constants import BROWNIE_PROJECT as B, MAX_ALLOCATE
from util.tok import TokSet

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
    _test_getSymbols()
    _test_getNFTVolumes(CO2_ADDR, startBlockNumber, endBlockNumber)
    _test_getveBalances(blockRange)
    _test_getAllocations(blockRange)
    _test_query(CO2_ADDR)
    _test_nft_infos()


def _foundConsume(CO2_ADDR, st, fin):
    DT_vols = query.getNFTVolumes(st, fin, CHAINID)
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
                allocation = (
                    oceanutil.veAllocate().getveAllocation(userAddr, nftAddr, chainId)
                    / MAX_ALLOCATE
                )
                assert allocations[chainId][nftAddr][userAddr] == allocation


@enforce_types
def _test_getSymbols():
    oceanToken = oceanutil.OCEANtoken()
    tokset = TokSet()
    tokset.add(CHAINID, oceanToken.address, "OCEAN")
    symbols_at_chain = query.getSymbols(
        tokset, CHAINID
    )  # dict of [basetoken_addr] : basetoken_symbol

    OCEAN_tok = tokset.tokAtSymbol(CHAINID, "OCEAN")
    assert symbols_at_chain[OCEAN_tok.address] == "OCEAN"


@enforce_types
def _test_getNFTVolumes(CO2_ADDR: str, st, fin):
    DT_vols = query.getNFTVolumes(st, fin, CHAINID)
    assert CO2_ADDR in DT_vols, (CO2_ADDR, DT_vols.keys())
    assert sum(DT_vols[CO2_ADDR].values()) > 0.0


@enforce_types
def _test_query(CO2_ADDR: str):
    st, fin, n = QUERY_ST, len(brownie.network.chain), 500
    rng = BlockRange(st, fin, n)
    (V0, SYM0) = query.query_all(rng, CHAINID)

    assert CO2_ADDR in V0
    assert SYM0


@enforce_types
def _test_nft_infos():
    nfts = query.getNFTInfos(CHAINID)
    assert len(nfts) > 0


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
def test_aquarius_asset_names():
    # test that we can get the asset names from aquarius
    nft_dids = [
        "did:op:6d2e99a4d4d501b6ebc0c60d0d6899305c4e8ecbc7293c132841e8d46832bd89",
        "did:op:8ce33d00d57633d641777f8d8e6c816c5ca0d3f198224305749b0069ce8709cf",
        "did:op:064abd2c7f8d5c3cacdbf43a687194d50008889130dbc4403d4b973797da7081",
        # ↓ invalid, should return ""
        "did:op:4aa86d2c10f9a352ac9ec062122e318d66be6777e9a37c982e46aab144bc1cfa",
    ]
    expectedAssetNames = ["Trent", "c2d fresh dataset", "CryptoPunks dataset C2D", ""]
    assetNames = query.aquarius_asset_names(nft_dids)
    assert len(assetNames) == 4

    for i in range(4):
        assert assetNames[nft_dids[i]] == expectedAssetNames[i]


@enforce_types
def test_filter_to_aquarius_assets():
    # test that we can get the asset names from aquarius
    nft_dids = [
        "did:op:6d2e99a4d4d501b6ebc0c60d0d6899305c4e8ecbc7293c132841e8d46832bd89",
        "did:op:8ce33d00d57633d641777f8d8e6c816c5ca0d3f198224305749b0069ce8709cf",
        "did:op:064abd2c7f8d5c3cacdbf43a687194d50008889130dbc4403d4b973797da7081",
        # ↓ invalid, should return ""
        "did:op:4aa86d2c10f9a352ac9ec062122e318d66be6777e9a37c982e46aab144bc1cfa",
    ]

    filtered_dids = query._filterToAquariusAssets(nft_dids)

    assert len(filtered_dids) == 3
    assert nft_dids[3] not in filtered_dids


@enforce_types
def test_filter_dids():
    # test that we can get the asset names from aquarius
    nft_dids = [
        "did:op:6d2e99a4d4d501b6ebc0c60d0d6899305c4e8ecbc7293c132841e8d46832bd89",
        "did:op:8ce33d00d57633d641777f8d8e6c816c5ca0d3f198224305749b0069ce8709cf",
        "did:op:064abd2c7f8d5c3cacdbf43a687194d50008889130dbc4403d4b973797da7081",
        # ↓ invalid, should filter out""
        "did:op:4aa86d2c10f9a352ac9ec062122e318d66be6777e9a37c982e46aab144bc1cfa",
        # ↓ purgatory asset, should filter out""
        "did:op:01bf34f4e44e0c0549c34bf241940d397fca57aa6107b481789845464866d7b7",
    ]

    filtered_dids = query._filterDids(nft_dids)

    assert len(filtered_dids) == 3
    assert nft_dids[3] not in filtered_dids
    assert nft_dids[4] not in filtered_dids


@enforce_types
def test_filter_nft_vols_to_aquarius_assets():
    oceanAddr = oceanutil.OCEAN_address()
    nftaddrs = [
        "0xfd97064e1038810c84faeb951097a1e2c8829ae0",
        "0xa550f42e80bc8a1d17e04223c4d21d650b227197",
        "0x2b4895e46970d3a2cae203d496d7b9905f707684",
        oceanAddr,  # invalid, should filter out this one
    ]

    # these addresses are from rinkeby
    chainID = 4

    # nftvols: dict of [basetoken_addr][nft_addr]:vol_amt
    nftvols = {}
    nftvols[oceanAddr] = {}
    for nftaddr in nftaddrs:
        nftvols[oceanAddr][nftaddr] = 1.0

    # filter out non-market assets
    nftvols_filtered = query._filterNftvols(nftvols, chainID)
    assert len(nftvols_filtered) == 1
    assert len(nftvols_filtered[oceanAddr]) == 3

    # match the addresses
    assert nftaddrs[0] in nftvols_filtered[oceanAddr]
    assert nftaddrs[1] in nftvols_filtered[oceanAddr]
    assert nftaddrs[2] in nftvols_filtered[oceanAddr]
    assert nftaddrs[3] not in nftvols_filtered[oceanAddr]


@enforce_types
def test_filter_out_purgatory():
    dids = [
        "did:op:01bf34f4e44e0c0549c34bf241940d397fca57aa6107b481789845464866d7b7",
        "did:op:01bf34f4e44e0c0549c34bf241940d397fca57aa6107b481789845464866d7b5",
    ]

    # filter out purgatory
    dids_filtered = query._filterOutPurgatory(dids)
    assert len(dids_filtered) == 1
    assert dids[1] in dids_filtered


@enforce_types
def test_filter_nftinfos():
    oceanAddr = oceanutil.OCEAN_address()
    addresses = [
        "0xbff8242de628cd45173b71022648617968bd0962",  # good
        "0x03894e05af1257714d1e06a01452d157e3a82202",  # purgatory
        oceanAddr,  # invalid
    ]

    # addresses are from polygon
    nfts = [query.DataNFT(addr, 137, "TEST") for addr in addresses]

    # filter
    nfts_filtered = query._filterNftinfos(nfts)

    assert len(nfts_filtered) == 1
    assert nfts[0] in nfts_filtered


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
