import os
import random
import time

import pytest
import brownie
from enforce_typing import enforce_types
from pytest import approx

from util import (
    calcrewards,
    csvs,
    dispense,
    oceanutil,
    oceantestutil,
    networkutil,
    query,
)
from util.allocations import allocsToStakes, loadStakes
from util.base18 import toBase18, fromBase18
from util.blockrange import BlockRange
from util.constants import BROWNIE_PROJECT as B, MAX_ALLOCATE
from util.tok import TokSet


PREV = {}
account0 = None
chain = None

CHAINID = networkutil.DEV_CHAINID
ADDRESS_FILE = networkutil.chainIdToAddressFile(networkutil.DEV_CHAINID)

DAY = 86400
WEEK = 7 * DAY
YEAR = 365 * DAY

# =========================================================================
# heavy on-chain tests: overall test


# pylint: disable=too-many-statements
@pytest.mark.timeout(300)
def test_all(tmp_path):
    """Run this all as a single test, because we may have to
    re-loop or sleep until the info we want is there."""

    CO2_sym = f"CO2_{random.randint(0,99999):05d}"
    CO2 = B.Simpletoken.deploy(CO2_sym, CO2_sym, 18, 1e26, {"from": account0})
    CO2_addr = CO2.address.lower()
    OCEAN = oceanutil.OCEANtoken()

    OCEAN_lock_amt = toBase18(5.0)

    accounts = _create_and_fund_random_accounts(7, [OCEAN, CO2], account0)

    sampling_test_accounts = [accounts.pop(), accounts.pop()]

    # Create data nfts
    data_nfts = []
    for i in range(5):
        (data_NFT, DT, exchangeId) = oceanutil.createDataNFTWithFRE(account0, CO2)
        assert oceanutil.FixedPrice().isActive(exchangeId) is True
        data_nfts.append((data_NFT, DT, exchangeId))

    _lock_and_allocate_ve(accounts, data_nfts, OCEAN_lock_amt)
    zerobal_delegation_test_acc = brownie.accounts.add()
    # account 0 delegates 50% to account 1, 5% to zerobal_delegation_test_acc
    oceanutil.ve_delegate(accounts[0], accounts[1], 0.5, 0)
    oceanutil.ve_delegate(accounts[0], zerobal_delegation_test_acc, 0.1, 1)

    # account 3 delegates 100% to account 4
    oceanutil.ve_delegate(accounts[3], accounts[4], 1.0, 0)
    # account 4 delegates 100% to account 3
    oceanutil.ve_delegate(accounts[4], accounts[3], 1.0, 0)
    # set start block number for querying
    ST = len(brownie.network.chain)

    # Consume
    for i, acc in enumerate(accounts):
        oceantestutil.buyDTFRE(data_nfts[i][2], 1.0, 10000.0, acc, CO2)
        oceantestutil.consumeDT(data_nfts[i][1], account0, acc)

    # ghost consume datanft 0
    ghost_consume_dt = data_nfts[0][1]
    ghost_consume_nft_addr = data_nfts[0][0].address.lower()
    ghost_consume_dt.mint(account0, toBase18(1000.0), {"from": account0})
    for _ in range(20):
        oceantestutil.consumeDT(ghost_consume_dt, account0, account0)

    _lock_and_allocate_ve(sampling_test_accounts, data_nfts, OCEAN_lock_amt)

    # keep deploying, until TheGraph node sees volume, or timeout
    # (assumes that with volume, everything else is there too
    for loop_i in range(50):
        FIN = len(brownie.network.chain)
        print(f"loop {loop_i} start")
        assert loop_i < 45, "timeout"
        if _foundConsume(CO2_addr, ST, FIN):
            break
        brownie.network.chain.sleep(10)
        brownie.network.chain.mine(10)
        time.sleep(2)

    brownie.network.chain.sleep(10)
    brownie.network.chain.mine(20)
    time.sleep(2)

    rng = BlockRange(ST, FIN, 100, 42)

    sampling_accounts_addrs = [a.address.lower() for a in sampling_test_accounts]
    delegation_accounts = [a.address.lower() for a in accounts[:2]]
    delegation_accounts.append(zerobal_delegation_test_acc.address.lower())

    # test single queries
    _test_getSymbols()
    _test_queryVolsOwners(CO2_addr, ST, FIN)
    _test_queryVebalances(rng, sampling_accounts_addrs, delegation_accounts)
    _test_queryAllocations(rng, sampling_accounts_addrs)
    _test_queryVolsOwnersSymbols(CO2_addr, ST, FIN)
    _test_queryNftinfo()

    # test dftool
    _test_dftool_query(tmp_path, ST, FIN)
    _test_dftool_nftinfo(tmp_path, FIN)
    _test_dftool_vebals(tmp_path, ST, FIN)
    _test_dftool_allocations(tmp_path, ST, FIN)

    # end-to-end tests
    _test_end_to_end_without_csvs(CO2_sym, rng)
    _test_end_to_end_with_csvs(CO2_sym, rng, tmp_path)

    # test ghost consume
    _test_ghost_consume(ST, FIN, rng, CO2_addr, ghost_consume_nft_addr)

    # modifies chain time, test last
    _test_queryPassiveRewards(sampling_accounts_addrs)

    # sleep 20 weeks
    brownie.network.chain.sleep(60 * 60 * 24 * 7 * 20)
    brownie.network.chain.mine(10)

    # check balances again
    _test_queryVebalances(rng, sampling_accounts_addrs, delegation_accounts)


# =========================================================================
# heavy on-chain tests: support functions


def _foundConsume(CO2_addr, st, fin):
    V0, _, _ = query._queryVolsOwners(st, fin, CHAINID)
    if CO2_addr not in V0:
        return False
    if sum(V0[CO2_addr].values()) == 0:
        return False

    # all good
    return True


# =========================================================================
# heavy on-chain tests: test single queries


@enforce_types
def _test_queryVebalances(
    rng: BlockRange, sampling_accounts: list, delegation_accounts: list
):
    veOCEAN = oceanutil.veOCEAN()

    veBalances, locked_amts, unlock_times = query.queryVebalances(rng, CHAINID)
    assert len(veBalances) > 0
    assert sum(veBalances.values()) > 0

    assert len(locked_amts) > 0
    assert sum(locked_amts.values()) > 0

    assert len(unlock_times) > 0
    assert sum(unlock_times.values()) > 0

    # find delegationaccounts[0], delegationaccounts[1] and delegationaccounts[2]
    # [0] delegates 50% to [1] and 5% to [2]
    assert sum(veBalances[acc] for acc in delegation_accounts) < 10
    assert veBalances[delegation_accounts[0]] * 100 / 45 * 1.5 == approx(
        veBalances[delegation_accounts[1]], 0.01
    )
    assert veBalances[delegation_accounts[0]] * 100 / 45 * 0.05 == approx(
        veBalances[delegation_accounts[2]], 0.01
    )

    for account in veBalances:
        bal = fromBase18(oceanutil.veDelegation().adjusted_balance_of(account))
        if account in sampling_accounts:
            assert veBalances[account] < bal
            continue
        assert veBalances[account] == approx(bal, rel=0.001, abs=1.0e-10)

        lock = veOCEAN.locked(account)
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
def _test_queryVolsOwners(CO2_addr: str, st, fin):
    V0, C0, _ = query._queryVolsOwners(st, fin, CHAINID)

    # test V0 (volumes)
    assert CO2_addr in V0, (CO2_addr, V0.keys())
    assert sum(V0[CO2_addr].values()) > 0.0

    # test C0 (owners)
    assert C0, (V0, C0)
    V0_nft_addrs = set(nft_addr for token_addr in V0 for nft_addr in V0[token_addr])
    for C0_nft_addr in C0:
        assert C0_nft_addr in V0_nft_addrs


@enforce_types
def _test_queryVolsOwnersSymbols(CO2_addr: str, st, fin):
    n = 500
    rng = BlockRange(st, fin, n)
    (V0, C0, SYM0) = query.queryVolsOwnersSymbols(rng, CHAINID)

    assert CO2_addr in V0
    assert C0
    assert SYM0


@enforce_types
def _test_queryNftinfo():
    nfts = query.queryNftinfo(CHAINID)
    assert len(nfts) > 0

    nfts_latest = query.queryNftinfo(CHAINID, "latest")
    assert len(nfts_latest) == len(nfts)

    nfts_block = query.queryNftinfo(137, 29778602)
    assert len(nfts_block) == 11


# =========================================================================
# heavy on-chain tests: test dftool


@enforce_types
def _test_dftool_query(tmp_path, ST, FIN):
    CSV_DIR = str(tmp_path)
    _clear_dir(CSV_DIR)

    # insert fake inputs: rate csv file
    csvs.saveRateCsv("OCEAN", 0.5, CSV_DIR)

    # main cmd
    NSAMP = 5

    cmd = f"./dftool volsym {ST} {FIN} {NSAMP} {CSV_DIR} {CHAINID}"
    os.system(cmd)

    # test result
    assert csvs.nftvolsCsvFilenames(CSV_DIR)
    assert csvs.ownersCsvFilenames(CSV_DIR)
    assert csvs.symbolsCsvFilenames(CSV_DIR)


@enforce_types
def _test_dftool_nftinfo(tmp_path, FIN):
    CSV_DIR = str(tmp_path)
    _clear_dir(CSV_DIR)

    cmd = f"./dftool nftinfo {CSV_DIR} {CHAINID} {FIN}"
    os.system(cmd)

    assert csvs.nftinfoCsvFilename(CSV_DIR, CHAINID)


@enforce_types
def _test_dftool_vebals(tmp_path, ST, FIN):
    CSV_DIR = str(tmp_path)
    _clear_dir(CSV_DIR)

    NSAMP = 100

    cmd = f"./dftool vebals {ST} {FIN} {NSAMP} {CSV_DIR} {CHAINID}"
    os.system(cmd)

    # test result
    vebals_csv = csvs.vebalsCsvFilename(CSV_DIR)
    assert os.path.exists(vebals_csv), "vebals csv file not found"

    # test without sampling
    cmd = f"./dftool vebals {ST} {FIN} 1 {CSV_DIR} {CHAINID}"  # NSAMP=1
    os.system(cmd)

    # test result
    vebals_csv = csvs.vebalsCsvFilename(CSV_DIR, False)
    assert os.path.exists(vebals_csv), "vebals_realtime csv not found"


@enforce_types
def _test_dftool_allocations(tmp_path, ST, FIN):
    CSV_DIR = str(tmp_path)
    _clear_dir(CSV_DIR)

    NSAMP = 100

    cmd = f"./dftool allocations {ST} {FIN} {NSAMP} {CSV_DIR} {CHAINID}"
    os.system(cmd)

    # test result
    allocations_csv = csvs.allocationCsvFilename(CSV_DIR)
    assert os.path.exists(allocations_csv), "allocations csv file not found"

    # test without sampling
    cmd = f"./dftool allocations {ST} {FIN} 1 {CSV_DIR} {CHAINID}"  # NSAMP=1
    os.system(cmd)

    # test result
    allocations_csv = csvs.allocationCsvFilename(CSV_DIR, False)
    assert os.path.exists(allocations_csv), "allocations_realtime csv not found"


# =========================================================================
# heavy on-chain tests: end-to-end


@enforce_types
def _test_end_to_end_without_csvs(CO2_sym, rng):
    (V0, C0, SYM0) = query.queryVolsOwnersSymbols(rng, CHAINID)
    V = {CHAINID: V0}
    C = {CHAINID: C0}
    SYM = {CHAINID: SYM0}

    vebals, _, _ = query.queryVebalances(rng, CHAINID)
    allocs = query.queryAllocations(rng, CHAINID)
    S = allocsToStakes(allocs, vebals)

    R = {"OCEAN": 0.5, "H2O": 1.618, CO2_sym: 1.0}

    m = float("inf")
    OCEAN_avail = 1e-5
    do_pubrewards = False
    do_rank = True

    rewardsperlp, _ = calcrewards.calcRewards(
        S, V, C, SYM, R, m, OCEAN_avail, do_pubrewards, do_rank
    )

    sum_ = sum(rewardsperlp[CHAINID].values())
    assert (abs(sum_ - OCEAN_avail) / OCEAN_avail) < 0.02


@enforce_types
def _test_end_to_end_with_csvs(CO2_sym, rng, tmp_path):
    csv_dir = str(tmp_path)
    _clear_dir(csv_dir)

    # 1. simulate "dftool getrate"
    csvs.saveRateCsv("OCEAN", 0.25, csv_dir)
    csvs.saveRateCsv("H2O", 1.61, csv_dir)
    csvs.saveRateCsv(CO2_sym, 1.00, csv_dir)

    # 2. simulate "dftool volsym"
    (V0, C0, SYM0) = query.queryVolsOwnersSymbols(rng, CHAINID)
    csvs.saveNftvolsCsv(V0, csv_dir, CHAINID)
    csvs.saveOwnersCsv(C0, csv_dir, CHAINID)
    csvs.saveSymbolsCsv(SYM0, csv_dir, CHAINID)
    V0 = C0 = SYM0 = None  # ensure not used later

    # 3. simulate "dftool allocations"
    allocs = query.queryAllocations(rng, CHAINID)
    csvs.saveAllocationCsv(allocs, csv_dir)
    allocs = None  # ensure not used later

    # 4. simulate "dftool vebals"
    vebals, locked_amt, unlock_time = query.queryVebalances(rng, CHAINID)
    csvs.saveVebalsCsv(vebals, locked_amt, unlock_time, csv_dir)
    vebals = locked_amt = unlock_time = None  # ensure not used later

    # 5. simulate "dftool calc"
    S = loadStakes(csv_dir)  # loads allocs & vebals, then *
    R = csvs.loadRateCsvs(csv_dir)
    V = csvs.loadNftvolsCsvs(csv_dir)
    C = csvs.loadOwnersCsvs(csv_dir)
    SYM = csvs.loadSymbolsCsvs(csv_dir)

    m = float("inf")
    OCEAN_avail = 1e-5
    do_pubrewards = False
    do_rank = True

    rewardsperlp, _ = calcrewards.calcRewards(
        S, V, C, SYM, R, m, OCEAN_avail, do_pubrewards, do_rank
    )

    sum_ = sum(rewardsperlp[CHAINID].values())
    assert (abs(sum_ - OCEAN_avail) / OCEAN_avail) < 0.02
    csvs.saveRewardsperlpCsv(rewardsperlp, csv_dir, "OCEAN")
    rewardsperlp = None  # ensure not used later

    # 6. simulate "dftool dispense_active"
    rewardsperlp = csvs.loadRewardsCsv(csv_dir, "OCEAN")
    dfrewards_addr = B.DFRewards.deploy({"from": account0}).address
    OCEAN_addr = oceanutil.OCEAN_address()
    dispense.dispense(rewardsperlp[CHAINID], dfrewards_addr, OCEAN_addr, account0)


@enforce_types
def _test_queryPassiveRewards(addresses):
    feeDistributor = oceanutil.FeeDistributor()
    OCEAN = oceanutil.OCEANtoken()

    def sim_epoch():
        OCEAN.transfer(
            feeDistributor.address,
            toBase18(1000.0),
            {"from": brownie.accounts[0]},
        )
        chain.sleep(WEEK)
        chain.mine()
        feeDistributor.checkpoint_token({"from": brownie.accounts[0]})
        feeDistributor.checkpoint_total_supply({"from": brownie.accounts[0]})

    for _ in range(3):
        sim_epoch()

    alice_last_reward = 0
    bob_last_reward = 0
    for _ in range(3):
        timestamp = chain.time() // WEEK * WEEK
        balances, rewards = query.queryPassiveRewards(timestamp, addresses)
        alice = addresses[0]
        bob = addresses[1]
        assert balances[alice] == balances[bob]
        assert rewards[alice] == rewards[bob]
        assert rewards[alice] > 0
        assert rewards[alice] > alice_last_reward
        assert rewards[bob] > bob_last_reward
        alice_last_reward = rewards[alice]
        bob_last_reward = rewards[bob]
        sim_epoch()


def _test_ghost_consume(ST, FIN, rng, CO2_addr, ghost_consume_nft_addr):
    (V0, _, _) = query.queryVolsOwnersSymbols(rng, CHAINID)
    assert V0[CO2_addr][ghost_consume_nft_addr] == approx(1.0, 0.5)
    (V0, _, _) = query._queryVolsOwners(ST, FIN, CHAINID)
    assert V0[CO2_addr][ghost_consume_nft_addr] == 21.0
    swaps = query._querySwaps(ST, FIN, CHAINID)
    assert swaps[CO2_addr][ghost_consume_nft_addr] == approx(1.0, 0.5)


# ===========================================================================
# non-heavy tests for query.py


@enforce_types
def test_empty_queryAllocations():
    rng = BlockRange(st=0, fin=10, num_samples=1)
    allocs = query.queryAllocations(rng, CHAINID)
    assert allocs == {}


@enforce_types
def test_empty_queryVebalances():
    rng = BlockRange(st=0, fin=10, num_samples=1)
    tup = query.queryVebalances(rng, CHAINID)
    assert tup == ({}, {}, {})


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

    allocations = allocations[CHAINID]

    for addr in allocate_addrs:
        assert addr in allocations, addr
        # Bob
        assert allocations[addr][bob.address.lower()] == approx((1 / 7), 0.1)

    # Alice
    _a = alice.address.lower()
    assert allocations[allocate_addrs[0]][_a] == approx(0.5, 0.03)
    assert allocations[allocate_addrs[3]][_a] == approx(0.5, 0.03)

    # Karen
    _k = karen.address.lower()
    assert allocations[allocate_addrs[0]][_k] == approx((0.1 * 6 / 7), 0.03)
    assert allocations[allocate_addrs[1]][_k] == approx((0.1 * 5 / 7), 0.03)
    assert allocations[allocate_addrs[2]][_k] == approx((0.2 * 4 / 7), 0.03)
    assert allocations[allocate_addrs[6]][_k] == approx((1 / 7), 0.03)

    # Carol
    _c = carol.address.lower()
    assert allocations[allocate_addrs[2]][_c] == approx((4 / 7), 0.03)
    assert allocations[allocate_addrs[6]][_c] == approx((1 / 7), 0.03)

    # James
    _j = james.address.lower()
    _j_expected = (
        0.1 * 1 / 7 + 0.2 * 1 / 7 + 0.3 * 1 / 7 + 0.05 * 1 / 7 + 0.5 * 1 / 7 + 1 / 7
    )
    assert allocations[allocate_addrs[0]][_j] == approx(_j_expected, 0.03)


def test_symbol():
    testToken = B.Simpletoken.deploy("CO2", "", 18, 1e26, {"from": account0})
    assert query.symbol(testToken.address) == "CO2"

    testToken = B.Simpletoken.deploy("ASDASDASD", "", 18, 1e26, {"from": account0})
    assert query.symbol(testToken.address) == "ASDASDASD"

    testToken = B.Simpletoken.deploy(
        "!@#$@!%$#^%$&~!@", "", 18, 1e26, {"from": account0}
    )
    assert query.symbol(testToken.address) == "!@#$@!%$#^%$&~!@"


@enforce_types
def test_queryAquariusAssetNames():
    nft_dids = [
        "did:op:6637c63a7be53c4d7c6204b92e1508c928f9090ca822cec42782c8b1ec33bb2f",
        "did:op:fa0e8fa9550e8eb13392d6eeb9ba9f8111801b332c8d2345b350b3bc66b379d5",
        "did:op:ce3f161fb98c64a2ded37fd34e25f28343f2c88d0c8205242df9c621770d4b3b",
        # ↓ invalid, should return ""
        "did:op:4aa86d2c10f9a352ac9ec062122e318d66be6777e9a37c982e46aab144bc1cfa",
    ]

    expectedAssetNames = [
        "OCEAN/USDT orderbook",
        "BTC/USDT orderbook",
        "DEX volume in details",
        "",
    ]
    assetNames = query.queryAquariusAssetNames(nft_dids)
    print("assetNames", assetNames)
    assert len(assetNames) == 4

    for i in range(4):
        assert expectedAssetNames.count(assetNames[nft_dids[i]]) == 1


@enforce_types
def test_filter_to_aquarius_assets():
    # test that we can get the asset names from aquarius
    nft_dids = [
        "did:op:6637c63a7be53c4d7c6204b92e1508c928f9090ca822cec42782c8b1ec33bb2f",
        "did:op:fa0e8fa9550e8eb13392d6eeb9ba9f8111801b332c8d2345b350b3bc66b379d5",
        "did:op:ce3f161fb98c64a2ded37fd34e25f28343f2c88d0c8205242df9c621770d4b3b",
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
        "did:op:6637c63a7be53c4d7c6204b92e1508c928f9090ca822cec42782c8b1ec33bb2f",
        "did:op:fa0e8fa9550e8eb13392d6eeb9ba9f8111801b332c8d2345b350b3bc66b379d5",
        "did:op:ce3f161fb98c64a2ded37fd34e25f28343f2c88d0c8205242df9c621770d4b3b",
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
        "0x84d8fec21b295baf3bf5998e6d01c067b43d061a",
        "0x4b23ee226f61eecc6521697b9e5d96e4bdfb1d0c",
        "0x9723488dc1524849a82917a61a38bbe24a8219c1",
        oceanAddr,  # invalid, should filter out this one
    ]

    # these addresses are from polygon
    chainID = 137

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
    addrs = [
        "0xbff8242de628cd45173b71022648617968bd0962",  # good
        "0x03894e05af1257714d1e06a01452d157e3a82202",  # purgatory
        oceanutil.OCEAN_address(),  # invalid
    ]
    # addresses are from polygon
    nfts = [query.SimpleDataNft(137, addr, "TEST", "0x123") for addr in addrs]

    # filter
    nfts_filtered = query._filterNftinfos(nfts)

    assert len(nfts_filtered) == 2
    assert nfts[0] in nfts_filtered
    assert nfts[1] in nfts_filtered  # shouldn't filter purgatory


@enforce_types
def test_mark_purgatory_nftinfos():
    addrs = [
        "0xbff8242de628cd45173b71022648617968bd0962",  # good
        "0x03894e05af1257714d1e06a01452d157e3a82202",  # purgatory
        oceanutil.OCEAN_address(),  # invalid
    ]
    # addresses are from polygon
    nfts = [query.SimpleDataNft(137, addr, "TEST", "0x123") for addr in addrs]

    nfts_marked = query._markPurgatoryNfts(nfts)

    assert len(nfts_marked) == 3
    assert nfts_marked[1].is_purgatory is True


@enforce_types
def test_populateNftAssetNames():
    nft_addr = "0xbff8242de628cd45173b71022648617968bd0962"
    nfts = [query.SimpleDataNft(137, nft_addr, "TEST", "0x123")]
    nfts = query._populateNftAssetNames(nfts)

    assert nfts[0].name == "Take a Ballet Lesson"


@enforce_types
def test_SimpleDataNFT():
    # test attributes
    nft_addr = "0xBff8242de628cd45173b71022648617968bd0962"
    nft = query.SimpleDataNft(137, nft_addr, "dn1", "0x123AbC")
    assert nft.chain_id == 137
    assert nft.nft_addr == nft_addr.lower()
    assert nft.symbol == "DN1"
    assert nft.owner_addr == "0x123abc"
    assert nft.name == ""
    assert not nft.is_purgatory
    assert isinstance(nft.did, str)

    # test __eq__
    nft2 = query.SimpleDataNft(137, nft_addr, "Dn1", "0x123abC")
    assert nft == nft2

    nft3 = query.SimpleDataNft(137, nft_addr, "DN2", "0x123abc")
    assert nft != nft3

    # test __repr__
    repr1 = repr(nft)
    repr2 = f"SimpleDataNft(137, '{nft_addr.lower()}', 'DN1', '0x123abc', False, '')"
    assert repr1 == repr2

    # test setName
    nft.setName("nAmE1")
    assert nft.name == "nAmE1"
    assert "nAmE1" in repr(nft)

    # non-default args in constructor
    nft4 = query.SimpleDataNft(137, nft_addr, "DN2", "0x123abc", True, "namE2")
    assert nft4.is_purgatory
    assert nft4.name == "namE2"


@enforce_types
def test_filter_by_max_volume():
    nftvols = {"a": {"b": 1000}}
    swapvols = {"a": {"b": 100}}
    filteredvols = query._filterbyMaxVolume(nftvols, swapvols)
    assert filteredvols["a"]["b"] == 100


# ===========================================================================
# support functions


@enforce_types
def _lock_and_allocate_ve(accounts, data_nfts, OCEAN_lock_amt):    
    OCEAN = oceanutil.OCEANtoken()
    veOCEAN = oceanutil.veOCEAN()
    veAllocate = oceanutil.veAllocate()

    t0 = chain.time()
    t1 = t0 // WEEK * WEEK + WEEK
    t2 = t1 + 4 * YEAR
    
    chain.sleep(t1 - t0)
    chain.mine()

    for acc in accounts:
        OCEAN.approve(veOCEAN.address, OCEAN_lock_amt, {"from": acc})
        veOCEAN.create_lock(OCEAN_lock_amt, t2, {"from": acc})

    # Allocate to data NFTs
    for i, acc in enumerate(accounts):
        veAllocate.setAllocation(100, data_nfts[i][0], 8996, {"from": acc})


@enforce_types
def _create_and_fund_random_accounts(
    num_accounts, tokens, mainaccount, tokenamt=1000.0
):
    accounts = []
    for _ in range(num_accounts):
        acc = brownie.accounts.add()
        accounts.append(acc)
        for token in tokens:
            token.transfer(acc, toBase18(tokenamt), {"from": mainaccount})
        mainaccount.transfer(acc, toBase18(0.1))
    return accounts


@enforce_types
def _clear_dir(csv_dir: str):
    """Remove the files inside csv_dir"""
    if csv_dir[-1] != "/":
        csv_dir += "/"
    cmd = f"rm {csv_dir}*"
    os.system(cmd)


@enforce_types
def setup_function():
    global account0, PREV, chain
    networkutil.connect(networkutil.DEV_CHAINID)
    chain = brownie.network.chain
    account0 = brownie.network.accounts[0]
    oceanutil.recordDevDeployedContracts()

    for envvar in ["ADDRESS_FILE", "SUBGRAPH_URI", "SECRET_SEED"]:
        PREV[envvar] = os.environ.get(envvar)

    os.environ["ADDRESS_FILE"] = ADDRESS_FILE
    os.environ["SUBGRAPH_URI"] = networkutil.chainIdToSubgraphUri(CHAINID)
    os.environ["SECRET_SEED"] = "1234"


@enforce_types
def teardown_function():
    global PREV
    
    networkutil.disconnect()

    for envvar, envval in PREV.items():
        if envval is None:
            del os.environ[envvar]
        else:
            os.environ[envvar] = envval

    PREV = {}
