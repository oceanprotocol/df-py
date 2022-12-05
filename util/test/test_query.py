import random
import time

import pytest
import brownie
from enforce_typing import enforce_types
from pytest import approx

from util import oceanutil, oceantestutil, networkutil, query
from util.base18 import toBase18, fromBase18
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

    CO2_sym = f"CO2_{random.randint(0,99999):05d}"
    CO2 = B.Simpletoken.deploy(CO2_sym, CO2_sym, 18, 1e26, {"from": account0})
    CO2_addr = CO2.address.lower()
    OCEAN = oceanutil.OCEANtoken()
    oceantestutil.fillAccountsWithToken(CO2)
    accounts = []
    publisher_account = account0
    OCEAN_lock_amt = toBase18(5.0)
    for i in range(7):
        accounts.append(brownie.network.accounts.add())
        CO2.transfer(accounts[i], toBase18(11000.0), {"from": account0})
        OCEAN.transfer(accounts[i], OCEAN_lock_amt, {"from": account0})
    sampling_test_accounts = [accounts.pop(), accounts.pop()]

    # Create data nfts
    data_nfts = []
    for i in range(5):
        (data_NFT, DT, exchangeId) = oceanutil.createDataNFTWithFRE(
            publisher_account, CO2
        )
        assert oceanutil.FixedPrice().isActive(exchangeId) is True
        data_nfts.append((data_NFT, DT, exchangeId))

    # Lock veOCEAN
    t0 = brownie.network.chain.time()
    t1 = t0 // WEEK * WEEK + WEEK
    t2 = t1 + WEEK * 20  # lock for 20 weeks
    brownie.network.chain.sleep(t1 - t0)
    for acc in accounts:
        oceanutil.create_ve_lock(OCEAN_lock_amt, t2, acc)

    # Allocate to data NFTs
    # pylint: disable=consider-using-enumerate
    for i in range(len(accounts)):
        oceanutil.set_allocation(
            100,
            data_nfts[i][0],
            8996,
            accounts[i],
        )

    # set start block number for querying
    startBlockNumber = len(brownie.network.chain)
    endBlockNumber = 0  # will be set later

    # Consume
    # pylint: disable=consider-using-enumerate
    for i in range(len(accounts)):
        oceantestutil.buyDTFRE(data_nfts[i][2], 1.0, 10000.0, accounts[i], CO2)
        oceantestutil.consumeDT(data_nfts[i][1], publisher_account, accounts[i])

    # sampling test accounts locks and allocates after start block
    # pylint: disable=consider-using-enumerate
    for i in range(len(sampling_test_accounts)):
        oceanutil.create_ve_lock(OCEAN_lock_amt, t2, sampling_test_accounts[i])
        oceanutil.set_allocation(100, data_nfts[i][0], 8996, sampling_test_accounts[i])

    # keep deploying, until TheGraph node sees volume, or timeout
    # (assumes that with volume, everything else is there too
    for loop_i in range(50):
        endBlockNumber = len(brownie.network.chain)
        print(f"loop {loop_i} start")
        assert loop_i < 5, "timeout"
        if _foundConsume(CO2_addr, startBlockNumber, endBlockNumber):
            break
        brownie.network.chain.sleep(10)
        brownie.network.chain.mine(10)
        time.sleep(2)

    brownie.network.chain.sleep(10)
    brownie.network.chain.mine(20)

    time.sleep(2)

    blockRange = BlockRange(startBlockNumber, endBlockNumber, 100, 42)

    sampling_accounts_addrs = [a.address.lower() for a in sampling_test_accounts]

    # run actual tests
    _test_getSymbols()
    _test_queryNftvolumes(CO2_addr, startBlockNumber, endBlockNumber)
    _test_queryVebalances(blockRange, sampling_accounts_addrs)
    _test_queryAllocations(blockRange, sampling_accounts_addrs)
    _test_queryNftvolsAndSymbols(CO2_addr)
    _test_queryNftinfo()


def _foundConsume(CO2_addr, st, fin):
    DT_vols = query._queryNftvolumes(st, fin, CHAINID)
    if CO2_addr not in DT_vols:
        return False
    if sum(DT_vols[CO2_addr].values()) == 0:
        return False

    # all good
    return True


@enforce_types
def _test_queryVebalances(rng: BlockRange, sampling_accounts: list):
    veBalances, locked_amts, unlock_times = query.queryVebalances(rng, CHAINID)
    assert len(veBalances) > 0
    assert sum(veBalances.values()) > 0

    assert len(locked_amts) > 0
    assert sum(locked_amts.values()) > 0

    assert len(unlock_times) > 0
    assert sum(unlock_times.values()) > 0

    for account in veBalances:
        bal = oceanutil.get_ve_balance(account) / 1e18
        if account in sampling_accounts:
            assert veBalances[account] < bal
            continue
        assert veBalances[account] == approx(bal, 0.001)

        lock = oceanutil.veOCEAN().locked(account)
        assert fromBase18(lock[0]) == locked_amts[account]
        assert lock[1] == unlock_times[account]


@enforce_types
def _test_queryAllocations(rng: BlockRange, sampling_accounts: list):
    allocations = query.queryAllocations(rng, CHAINID)

    assert len(allocations) > 0

    for chainId in allocations:
        for nftAddr in allocations[chainId]:
            for userAddr in allocations[chainId][nftAddr]:
                allocation_contract = (
                    oceanutil.veAllocate().getveAllocation(userAddr, nftAddr, chainId)
                    / MAX_ALLOCATE
                )
                allocation_query = allocations[chainId][nftAddr][userAddr]
                if userAddr in sampling_accounts:
                    assert allocation_query < allocation_contract
                    continue
                assert allocation_query == approx(allocation_contract, 1e-7)


@enforce_types
def _test_getSymbols():
    oceanToken = oceanutil.OCEANtoken()
    tokset = TokSet()
    tokset.add(CHAINID, oceanToken.address.lower(), "OCEAN")
    symbols_at_chain = query.getSymbols(
        tokset, CHAINID
    )  # dict of [basetoken_addr] : basetoken_symbol

    OCEAN_tok = tokset.tokAtSymbol(CHAINID, "OCEAN")
    assert symbols_at_chain[OCEAN_tok.address] == "OCEAN"


@enforce_types
def _test_queryNftvolumes(CO2_addr: str, st, fin):
    DT_vols = query._queryNftvolumes(st, fin, CHAINID)
    assert CO2_addr in DT_vols, (CO2_addr, DT_vols.keys())
    assert sum(DT_vols[CO2_addr].values()) > 0.0


@enforce_types
def _test_queryNftvolsAndSymbols(CO2_addr: str):
    st, fin, n = QUERY_ST, len(brownie.network.chain), 500
    rng = BlockRange(st, fin, n)
    (V0, SYM0) = query.queryNftvolsAndSymbols(rng, CHAINID)

    assert CO2_addr in V0
    assert SYM0


@enforce_types
def _test_queryNftinfo():
    nfts = query.queryNftinfo(CHAINID)
    assert len(nfts) > 0


# pylint: disable=too-many-statements
@enforce_types
def test_allocation_sampling():
    alice, bob, carol, karen, james = [brownie.accounts.add() for _ in range(5)]
    account0.transfer(alice, "1 ether")
    account0.transfer(bob, "1 ether")
    account0.transfer(carol, "1 ether")
    account0.transfer(karen, "1 ether")
    account0.transfer(james, "1 ether")

    allocate_addrs = [
        f"0x000000000000000000000000000000000000000{i}" for i in range(1, 8)
    ]

    # Alice allocates at 0-0 and 3.5-3
    # Bob allocates at 0-0 1-1 2-2 3-3 4-4 5-5 6-6 100%
    # Carol allocates at 2-2 6-2 100%
    # Karen allocates at 10% 0-0, 20% 2-2 and 100% 6-6
    # James allocates 10% 0-0, 20% 1-0, 30% 2-0, 5% 3-0, 50% 4-0, 0% 5-0, 100% 6-0

    def forward(blocks):
        brownie.network.chain.sleep(1)
        brownie.network.chain.mine(blocks)

    start_block = len(brownie.network.chain)

    # DAY 0
    oceanutil.set_allocation(10000, allocate_addrs[0], 8996, alice)  # 100% at 0
    oceanutil.set_allocation(10000, allocate_addrs[0], 8996, bob)  # 100% at 0
    oceanutil.set_allocation(1000, allocate_addrs[0], 8996, karen)  # 10% at 0
    oceanutil.set_allocation(1000, allocate_addrs[0], 8996, james)  # 10% at 0

    forward(100)

    # DAY 1
    # Bob removes and re-adds 100%
    oceanutil.set_allocation(0, allocate_addrs[0], 8996, bob)  # 0% at 1
    oceanutil.set_allocation(10000, allocate_addrs[1], 8996, bob)  # 100% at 1

    # Karen allocates 10%
    oceanutil.set_allocation(1000, allocate_addrs[1], 8996, karen)  # 10% at 1

    # James allocates 20%
    oceanutil.set_allocation(2000, allocate_addrs[0], 8996, james)  # 20% at 1

    forward(100)

    # DAY 2
    # Bob removes and re-adds 100%
    oceanutil.set_allocation(0, allocate_addrs[1], 8996, bob)
    oceanutil.set_allocation(10000, allocate_addrs[2], 8996, bob)

    # Carol allocates 100%
    oceanutil.set_allocation(10000, allocate_addrs[2], 8996, carol)

    # Karen allocates 20%
    oceanutil.set_allocation(2000, allocate_addrs[2], 8996, karen)

    # James allocates 30%
    oceanutil.set_allocation(3000, allocate_addrs[0], 8996, james)
    forward(100)

    # DAY 3

    # Bob removes and re-adds 100%
    oceanutil.set_allocation(0, allocate_addrs[2], 8996, bob)
    oceanutil.set_allocation(10000, allocate_addrs[3], 8996, bob)

    # James allocates 5%
    oceanutil.set_allocation(500, allocate_addrs[0], 8996, james)

    forward(50)

    # DAY 3.5
    # Alice allocates 100%
    oceanutil.set_allocation(0, allocate_addrs[0], 8996, alice)
    oceanutil.set_allocation(10000, allocate_addrs[3], 8996, alice)

    forward(50)

    # DAY 4
    # Bob removes and re-adds 100%
    oceanutil.set_allocation(0, allocate_addrs[3], 8996, bob)
    oceanutil.set_allocation(10000, allocate_addrs[4], 8996, bob)

    # James allocates 50%
    oceanutil.set_allocation(5000, allocate_addrs[0], 8996, james)

    forward(100)

    # DAY 5

    # Bob removes and re-adds 100%
    oceanutil.set_allocation(0, allocate_addrs[4], 8996, bob)
    oceanutil.set_allocation(10000, allocate_addrs[5], 8996, bob)

    # James allocates 0%
    oceanutil.set_allocation(0, allocate_addrs[0], 8996, james)

    forward(100)

    # DAY 6
    # Bob removes and re-adds 100%
    oceanutil.set_allocation(0, allocate_addrs[5], 8996, bob)
    oceanutil.set_allocation(10000, allocate_addrs[6], 8996, bob)

    # Carol allocates 100%
    oceanutil.set_allocation(0, allocate_addrs[2], 8996, carol)
    oceanutil.set_allocation(10000, allocate_addrs[6], 8996, carol)

    # Karen allocates 100%
    oceanutil.set_allocation(0, allocate_addrs[0], 8996, karen)
    oceanutil.set_allocation(0, allocate_addrs[1], 8996, karen)
    oceanutil.set_allocation(0, allocate_addrs[2], 8996, karen)
    oceanutil.set_allocation(10000, allocate_addrs[6], 8996, karen)

    # James allocates 100%
    oceanutil.set_allocation(10000, allocate_addrs[0], 8996, james)

    # FIN
    forward(100)
    end_block = len(brownie.network.chain)

    # query
    rng = BlockRange(start_block, end_block, end_block - start_block, 42)

    allocations = None
    while True:
        try:
            allocations = query.queryAllocations(rng, CHAINID)
        # pylint: disable=bare-except
        except:
            pass
        if allocations is not None and len(allocations) > 0:
            break
        time.sleep(1)
        forward(5)

    allocations = allocations[str(CHAINID)]

    for addr in allocate_addrs:
        assert addr in allocations, addr
        # Bob
        assert allocations[addr][bob.address.lower()] == approx(1 / 7, 0.1)

    # Alice
    _a = alice.address.lower()
    assert allocations[allocate_addrs[0]][_a] == approx(0.5, 0.03)
    assert allocations[allocate_addrs[3]][_a] == approx(0.5, 0.03)

    # Karen
    _k = karen.address.lower()
    assert allocations[allocate_addrs[0]][_k] == approx(0.1 * 6 / 7, 0.03)
    assert allocations[allocate_addrs[1]][_k] == approx(0.1 * 5 / 7, 0.03)
    assert allocations[allocate_addrs[2]][_k] == approx(0.2 * 4 / 7, 0.03)
    assert allocations[allocate_addrs[6]][_k] == approx(1 / 7, 0.03)

    # Carol
    _c = carol.address.lower()
    assert allocations[allocate_addrs[2]][_c] == approx(4 / 7, 0.03)
    assert allocations[allocate_addrs[6]][_c] == approx(1 / 7, 0.03)

    # James
    _j = james.address.lower()
    _j_expected = (
        0.1 * 1 / 7 + 0.2 * 1 / 7 + 0.3 * 1 / 7 + 0.05 * 1 / 7 + 0.5 * 1 / 7 + 1 / 7
    )
    assert allocations[allocate_addrs[0]][_j] == approx(_j_expected, 0.03)


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
def test_queryAquariusAssetNames():
    # test that we can get the asset names from aquarius
    nft_dids = [
        "did:op:6d2e99a4d4d501b6ebc0c60d0d6899305c4e8ecbc7293c132841e8d46832bd89",
        "did:op:8ce33d00d57633d641777f8d8e6c816c5ca0d3f198224305749b0069ce8709cf",
        "did:op:064abd2c7f8d5c3cacdbf43a687194d50008889130dbc4403d4b973797da7081",
        # ↓ invalid, should return ""
        "did:op:4aa86d2c10f9a352ac9ec062122e318d66be6777e9a37c982e46aab144bc1cfa",
    ]
    expectedAssetNames = ["Trent", "c2d fresh dataset", "CryptoPunks dataset C2D", ""]
    assetNames = query.queryAquariusAssetNames(nft_dids)
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

    assert len(nfts_filtered) == 2
    assert nfts[0] in nfts_filtered
    assert nfts[1] in nfts_filtered  # shouldn't filter purgatory


@enforce_types
def test_mark_purgatory_nftinfos():
    oceanAddr = oceanutil.OCEAN_address()
    addresses = [
        "0xbff8242de628cd45173b71022648617968bd0962",  # good
        "0x03894e05af1257714d1e06a01452d157e3a82202",  # purgatory
        oceanAddr,  # invalid
    ]

    # addresses are from polygon
    nfts = [query.DataNFT(addr, 137, "TEST") for addr in addresses]

    nfts_marked = query._markPurgatoryNfts(nfts)

    assert len(nfts_marked) == 3
    assert nfts_marked[1].is_purgatory is True


@enforce_types
def test_populateNftAssetNames():
    nfts = [query.DataNFT("0xbff8242de628cd45173b71022648617968bd0962", 137, "TEST")]
    nfts = query._populateNftAssetNames(nfts)

    assert nfts[0].name == "Take a Ballet Lesson"


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
