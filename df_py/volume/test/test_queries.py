# mypy: disable-error-code="attr-defined"
# pylint: disable=too-many-lines
import os
import random
import time

import brownie
import pytest
from enforce_typing import enforce_types
from pytest import approx

from df_py.util import dispense, networkutil, oceantestutil, oceanutil
from df_py.util.base18 import from_wei, str_with_wei, to_wei
from df_py.util.blockrange import BlockRange
from df_py.util.constants import BROWNIE_PROJECT as B
from df_py.util.constants import MAX_ALLOCATE
from df_py.util.oceanutil import ve_delegate
from df_py.volume import calc_rewards, csvs, queries
from df_py.volume.allocations import allocs_to_stakes, load_stakes
from df_py.volume.models import SimpleDataNft, TokSet

PREV = {}
god_acct = None
chain = None
OCEAN, veOCEAN = None, None
CO2, CO2_addr, CO2_sym = None, None, None

CHAINID = networkutil.DEV_CHAINID
ADDRESS_FILE = networkutil.chain_id_to_address_file(CHAINID)

DAY = 86400
WEEK = 7 * DAY
YEAR = 365 * DAY


class SimpleAsset:
    def __init__(self, tup):
        self.nft, self.dt, self.exchangeId = tup
        assert oceanutil.FixedPrice().isActive(self.exchangeId)


# =========================================================================
# heavy on-chain tests: overall test


# pylint: disable=too-many-statements
@pytest.mark.timeout(300)
def test_all(tmp_path):
    """Run this all as a single test, because we may have to
    re-loop or sleep until the info we want is there."""

    _deploy_CO2()

    print("Create accts...")
    accounts = [brownie.accounts.add() for i in range(5)]
    sampling_accounts = [brownie.accounts.add() for i in range(2)]
    zerobal_delegation_acct = brownie.accounts.add()

    _fund_accts(accounts + sampling_accounts, amt_to_fund=1000.0)

    assets = _create_assets(n_assets=5)

    print("Sleep & mine")
    t0 = chain.time()
    t1 = t0 // WEEK * WEEK + WEEK
    t2 = t1 + 4 * YEAR
    chain.sleep(t1 - t0)
    chain.mine()

    lock_amt = 5.0
    _lock(accounts, lock_amt, t2)

    _allocate(accounts, assets)

    print("Delegate...")
    ve_delegate(accounts[0], accounts[1], 0.5, 0)  # 0 -> 1 50%
    print(f"  {accounts[0].address} -> {accounts[1].address} 50%")
    ve_delegate(accounts[0], zerobal_delegation_acct, 0.1, 1)  # 0 -> zerobal 5%
    print(f"  {accounts[0].address} -> {zerobal_delegation_acct.address} 10%")
    ve_delegate(accounts[3], accounts[4], 1.0, 0)  # 3 -> 4 100%
    print(f"  {accounts[3].address} -> {accounts[4].address} 100%")
    ve_delegate(accounts[4], accounts[3], 1.0, 0)  # 4 -> 3 100%
    print(f"  {accounts[4].address} -> {accounts[3].address} 100%")

    start_block = len(chain)
    print(f"ST = start block for querying = {start_block}")

    # these accounts are used to test if sampling the range works
    # this is why we're calling the following functions after setting ST
    _lock(sampling_accounts, lock_amt * 100, t2)
    _allocate(sampling_accounts, assets)

    print("Consume...")
    for i, acct in enumerate(accounts):
        oceantestutil.buy_DT_FRE(assets[i].exchangeId, 1.0, 10000.0, acct, CO2)
        oceantestutil.consume_DT(assets[i].dt, god_acct, acct)

    print("Ghost consume...")
    ghost_consume_asset = assets[0]
    ghost_consume_nft_addr = ghost_consume_asset.nft.address.lower()
    ghost_consume_asset.dt.mint(god_acct, to_wei(1000.0), {"from": god_acct})
    for _ in range(20):
        oceantestutil.consume_DT(ghost_consume_asset.dt, god_acct, god_acct)

    print("Keep sampling until enough volume (or timeout)")
    for loop_i in range(50):
        fin_block = len(chain)
        print(f"  loop {loop_i} start")
        assert loop_i < 45, "timeout"
        # this test assumes that all actions before consume will
        # be on the graph too. Eg veOCEAN allocation or delegation
        if _found_consume(start_block, fin_block):
            break
        chain.sleep(10)
        chain.mine(10)
        time.sleep(2)

    chain.sleep(10)
    chain.mine(20)
    time.sleep(2)

    rng = BlockRange(start_block, fin_block, 100, 42)
    sampling_accounts_addrs = [a.address.lower() for a in sampling_accounts]
    delegation_accounts = [a.address.lower() for a in accounts[:2]]
    delegation_accounts.append(zerobal_delegation_acct.address.lower())

    # test single queries
    _test_getSymbols()
    _test_queryVolsOwners(start_block, fin_block)
    _test_queryVebalances(rng, sampling_accounts_addrs, delegation_accounts)
    _test_queryAllocations(rng, sampling_accounts_addrs)
    _test_queryVolsOwnersSymbols(start_block, fin_block)

    # test dftool
    _test_dftool_query(tmp_path, start_block, fin_block)
    _test_dftool_nftinfo(tmp_path, fin_block)
    _test_dftool_vebals(tmp_path, start_block, fin_block)
    _test_dftool_allocations(tmp_path, start_block, fin_block)

    # end-to-end tests
    _test_end_to_end_without_csvs(rng)
    _test_end_to_end_with_csvs(rng, tmp_path)

    # test ghost consume
    _test_ghost_consume(start_block, fin_block, rng, ghost_consume_nft_addr)

    # modifies chain time, test last
    _test_queryPassiveRewards(sampling_accounts_addrs)

    # sleep 20 weeks
    chain.sleep(60 * 60 * 24 * 7 * 20)
    chain.mine(10)

    # check balances again
    _test_queryVebalances(rng, sampling_accounts_addrs, delegation_accounts)

    # Running this test before other tests causes the following error:
    #   brownie.exceptions.ContractNotFound: This contract no longer exists.
    _test_queryNftinfo()


# =========================================================================
# heavy on-chain tests: support functions


def _deploy_CO2():
    print("Deploy CO2 token...")
    global CO2, CO2_addr, CO2_sym
    CO2_sym = f"CO2_{random.randint(0,99999):05d}"
    CO2 = B.Simpletoken.deploy(CO2_sym, CO2_sym, 18, 1e26, {"from": god_acct})
    CO2_addr = CO2.address.lower()


def _found_consume(st, fin):
    V0, _, _ = queries._queryVolsOwners(st, fin, CHAINID)

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
    print("_test_queryVebalances()...")

    veBalances, locked_amts, unlock_times = queries.queryVebalances(rng, CHAINID)
    assert len(veBalances) > 0
    assert sum(veBalances.values()) > 0

    assert len(locked_amts) > 0
    assert sum(locked_amts.values()) > 0

    assert len(unlock_times) > 0
    assert sum(unlock_times.values()) > 0

    # find delegation_accounts[0], delegation_accounts[1] and delegation_accounts[2]
    # [0] delegates 50% to [1] and 5% to [2]
    assert sum(veBalances[acc] for acc in delegation_accounts) < 10
    assert veBalances[delegation_accounts[0]] * 100 / 45 * 1.5 == approx(
        veBalances[delegation_accounts[1]], 0.01
    )
    assert veBalances[delegation_accounts[0]] * 100 / 45 * 0.05 == approx(
        veBalances[delegation_accounts[2]], 0.01
    )

    for account in veBalances:
        bal = from_wei(oceanutil.veDelegation().adjusted_balance_of(account))
        if account in sampling_accounts:
            assert veBalances[account] < bal
            continue
        assert veBalances[account] == approx(bal, rel=0.001, abs=1.0e-10)

        lock = veOCEAN.locked(account)
        assert from_wei(lock[0]) == locked_amts[account]
        assert lock[1] == unlock_times[account]


@enforce_types
def _test_queryAllocations(rng: BlockRange, sampling_accounts: list):
    print("_test_queryAllocations()...")
    allocations = queries.queryAllocations(rng, CHAINID)

    assert len(allocations) > 0

    for chain_id in allocations:
        for nftAddr in allocations[chain_id]:
            for userAddr in allocations[chain_id][nftAddr]:
                allocation_contract = (
                    oceanutil.veAllocate().getveAllocation(userAddr, nftAddr, chain_id)
                    / MAX_ALLOCATE
                )
                allocation_query = allocations[chain_id][nftAddr][userAddr]
                if userAddr in sampling_accounts:
                    assert allocation_query < allocation_contract
                    continue
                assert allocation_query == approx(allocation_contract, 1e-7)


@enforce_types
def _test_getSymbols():
    print("_test_getSymbols()...")
    OCEAN_token = oceanutil.OCEAN_token()
    token_set = TokSet()
    token_set.add(CHAINID, OCEAN_token.address.lower(), "OCEAN")
    symbols_at_chain = queries.getSymbols(
        token_set, CHAINID
    )  # dict of [basetoken_addr] : basetoken_symbol

    OCEAN_tok = token_set.tok_at_symbol(CHAINID, "OCEAN")
    assert symbols_at_chain[OCEAN_tok.address] == "OCEAN"


@enforce_types
def _test_queryVolsOwners(st, fin):
    print("_test_queriesVolsOwners()...")
    V0, C0, _ = queries._queryVolsOwners(st, fin, CHAINID)

    # test V0 (volumes)
    assert CO2_addr in V0, (CO2_addr, V0.keys())
    assert sum(V0[CO2_addr].values()) > 0.0

    # test C0 (owners)
    assert C0, (V0, C0)
    V0_nft_addrs = set(nft_addr for token_addr in V0 for nft_addr in V0[token_addr])
    for C0_nft_addr in C0:
        assert C0_nft_addr in V0_nft_addrs


@enforce_types
def _test_queryVolsOwnersSymbols(st, fin):
    print("_test_queryVolsOwnersSymbols()...")
    n = 500
    rng = BlockRange(st, fin, n)
    (V0, C0, SYM0) = queries.queryVolsOwnersSymbols(rng, CHAINID)

    assert CO2_addr in V0
    assert C0
    assert SYM0


@enforce_types
def _test_queryNftinfo():
    print("_test_queryNftinfo()...")

    nfts_block = queries.queryNftinfo(137, 29778602)
    assert len(nfts_block) == 9

    nfts = queries.queryNftinfo(CHAINID)
    assert len(nfts) > 0

    nfts_latest = queries.queryNftinfo(CHAINID, "latest")
    assert len(nfts_latest) == len(nfts)


# =========================================================================
# heavy on-chain tests: test dftool


@enforce_types
def _test_dftool_query(tmp_path, start_block, fin_block):
    print("_test_dftool_query()...")
    csv_dir = str(tmp_path)
    _clear_dir(csv_dir)

    # insert fake inputs: rate csv file
    csvs.save_rate_csv("OCEAN", 0.5, csv_dir)

    # main cmd
    n_samp = 5

    cmd = f"./dftool volsym {start_block} {fin_block} {n_samp} {csv_dir} {CHAINID}"
    os.system(cmd)

    # test result
    assert csvs.nftvols_csv_filenames(csv_dir)
    assert csvs.owners_csv_filenames(csv_dir)
    assert csvs.symbols_csv_filenames(csv_dir)


@enforce_types
def _test_dftool_nftinfo(tmp_path, fin_block):
    print("_test_nftinfo()...")
    csv_dir = str(tmp_path)
    _clear_dir(csv_dir)

    cmd = f"./dftool nftinfo {csv_dir} {CHAINID} --FIN {fin_block}"
    os.system(cmd)

    assert csvs.nftinfo_csv_filename(csv_dir, CHAINID)


@enforce_types
def _test_dftool_vebals(tmp_path, start_block, fin_block):
    print("_test_vebals()...")
    csv_dir = str(tmp_path)
    _clear_dir(csv_dir)

    n_samp = 100

    cmd = f"./dftool vebals {start_block} {fin_block} {n_samp} {csv_dir} {CHAINID}"
    os.system(cmd)

    # test result
    vebals_csv = csvs.vebals_csv_filename(csv_dir)
    assert os.path.exists(vebals_csv), "vebals csv file not found"

    # test without sampling
    cmd = f"./dftool vebals {start_block} {fin_block} 1 {csv_dir} {CHAINID}"  # NSAMP=1
    os.system(cmd)

    # test result
    vebals_csv = csvs.vebals_csv_filename(csv_dir, False)
    assert os.path.exists(vebals_csv), "vebals_realtime csv not found"


@enforce_types
def _test_dftool_allocations(tmp_path, start_block, fin_block):
    print("_test_allocations()...")
    csv_dir = str(tmp_path)
    _clear_dir(csv_dir)

    n_samp = 100

    cmd = f"./dftool allocations {start_block} {fin_block} {n_samp} {csv_dir} {CHAINID}"
    os.system(cmd)

    # test result
    allocations_csv = csvs.allocation_csv_filename(csv_dir)
    assert os.path.exists(allocations_csv), "allocations csv file not found"

    # test without sampling
    cmd = f"./dftool allocations {start_block} {fin_block} 1 {csv_dir} {CHAINID}"  # NSAMP=1
    os.system(cmd)

    # test result
    allocations_csv = csvs.allocation_csv_filename(csv_dir, False)
    assert os.path.exists(allocations_csv), "allocations_realtime csv not found"


# =========================================================================
# heavy on-chain tests: end-to-end


@enforce_types
def _test_end_to_end_without_csvs(rng):
    print("_test_end_to_end_without_csvs()...")
    (V0, C0, SYM0) = queries.queryVolsOwnersSymbols(rng, CHAINID)
    V = {CHAINID: V0}
    C = {CHAINID: C0}
    SYM = {CHAINID: SYM0}

    vebals, _, _ = queries.queryVebalances(rng, CHAINID)
    allocs = queries.queryAllocations(rng, CHAINID)
    S = allocs_to_stakes(allocs, vebals)

    R = {"OCEAN": 0.5, "H2O": 1.618, CO2_sym: 1.0}

    m = float("inf")
    OCEAN_avail = 1e-5
    do_pubrewards = False
    do_rank = True

    rewardsperlp, _ = calc_rewards.calc_rewards(
        S, V, C, SYM, R, m, OCEAN_avail, do_pubrewards, do_rank
    )

    sum_ = sum(rewardsperlp[CHAINID].values())
    assert (abs(sum_ - OCEAN_avail) / OCEAN_avail) < 0.02


@enforce_types
def _test_end_to_end_with_csvs(rng, tmp_path):
    print("_test_end_to_end_with_csvs()...")
    csv_dir = str(tmp_path)
    _clear_dir(csv_dir)

    # 1. simulate "dftool get_rate"
    csvs.save_rate_csv("OCEAN", 0.25, csv_dir)
    csvs.save_rate_csv("H2O", 1.61, csv_dir)
    csvs.save_rate_csv(CO2_sym, 1.00, csv_dir)

    # 2. simulate "dftool volsym"
    (V0, C0, SYM0) = queries.queryVolsOwnersSymbols(rng, CHAINID)
    csvs.save_nftvols_csv(V0, csv_dir, CHAINID)
    csvs.save_owners_csv(C0, csv_dir, CHAINID)
    csvs.save_symbols_csv(SYM0, csv_dir, CHAINID)
    V0 = C0 = SYM0 = None  # ensure not used later

    # 3. simulate "dftool allocations"
    allocs = queries.queryAllocations(rng, CHAINID)
    csvs.save_allocation_csv(allocs, csv_dir)
    allocs = None  # ensure not used later

    # 4. simulate "dftool vebals"
    vebals, locked_amt, unlock_time = queries.queryVebalances(rng, CHAINID)
    csvs.save_vebals_csv(vebals, locked_amt, unlock_time, csv_dir)
    vebals = locked_amt = unlock_time = None  # ensure not used later

    # 5. simulate "dftool calc"
    S = load_stakes(csv_dir)  # loads allocs & vebals, then *
    R = csvs.load_rate_csvs(csv_dir)
    V = csvs.load_nftvols_csvs(csv_dir)
    C = csvs.load_owners_csvs(csv_dir)
    SYM = csvs.load_symbols_csvs(csv_dir)

    m = float("inf")
    OCEAN_avail = 1e-5
    do_pubrewards = False
    do_rank = True

    rewardsperlp, _ = calc_rewards.calc_rewards(
        S, V, C, SYM, R, m, OCEAN_avail, do_pubrewards, do_rank
    )

    sum_ = sum(rewardsperlp[CHAINID].values())
    assert (abs(sum_ - OCEAN_avail) / OCEAN_avail) < 0.02
    csvs.save_volume_rewards_csv(rewardsperlp, csv_dir)
    rewardsperlp = None  # ensure not used later

    # 6. simulate "dftool dispense_active"
    rewardsperlp = csvs.load_volume_rewards_csv(csv_dir)
    dfrewards_addr = B.DFRewards.deploy({"from": god_acct}).address
    OCEAN_addr = oceanutil.OCEAN_address()
    dispense.dispense(rewardsperlp[CHAINID], dfrewards_addr, OCEAN_addr, god_acct)


@enforce_types
def _test_queryPassiveRewards(addresses):
    print("_test_queryPassiveRewards()...")
    fee_distributor = oceanutil.FeeDistributor()

    def sim_epoch():
        OCEAN.transfer(
            fee_distributor.address,
            to_wei(1000.0),
            {"from": god_acct},
        )
        chain.sleep(WEEK)
        chain.mine()
        fee_distributor.checkpoint_token({"from": god_acct})
        fee_distributor.checkpoint_total_supply({"from": god_acct})

    for _ in range(3):
        sim_epoch()

    alice_last_reward = 0
    bob_last_reward = 0
    for _ in range(3):
        timestamp = chain.time() // WEEK * WEEK
        balances, rewards = queries.queryPassiveRewards(timestamp, addresses)
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


def _test_ghost_consume(start_block, fin_block, rng, ghost_consume_nft_addr):
    print("_test_ghost_consume()...")
    (V0, _, _) = queries.queryVolsOwnersSymbols(rng, CHAINID)
    assert V0[CO2_addr][ghost_consume_nft_addr] == approx(1.0, 0.5)

    (V0, _, _) = queries._queryVolsOwners(start_block, fin_block, CHAINID)
    assert V0[CO2_addr][ghost_consume_nft_addr] == 21.0

    swaps = queries._querySwaps(start_block, fin_block, CHAINID)
    assert swaps[CO2_addr][ghost_consume_nft_addr] == approx(1.0, 0.5)


# ===========================================================================
# non-heavy tests for query.py. Don't need to lump these into "test_all()"


@enforce_types
def test_queryAllocations_empty():
    rng = BlockRange(st=0, fin=10, num_samples=1)
    allocs = queries.queryAllocations(rng, CHAINID)
    assert allocs == {}


@enforce_types
def test_queryVebalances_empty():
    rng = BlockRange(st=0, fin=10, num_samples=1)
    tup = queries.queryVebalances(rng, CHAINID)
    assert tup == ({}, {}, {})


# pylint: disable=too-many-statements
@enforce_types
def test_allocation_sampling():
    alice, bob, carol, karen, james = [brownie.accounts.add() for _ in range(5)]
    god_acct.transfer(alice, "1 ether")
    god_acct.transfer(bob, "1 ether")
    god_acct.transfer(carol, "1 ether")
    god_acct.transfer(karen, "1 ether")
    god_acct.transfer(james, "1 ether")

    allocate_addrs = [
        f"0x000000000000000000000000000000000000000{i}" for i in range(1, 8)
    ]

    # Alice allocates at 0-0 and 3.5-3
    # Bob allocates at 0-0 1-1 2-2 3-3 4-4 5-5 6-6 100%
    # Carol allocates at 2-2 6-2 100%
    # Karen allocates at 10% 0-0, 20% 2-2 and 100% 6-6
    # James allocates 10% 0-0, 20% 1-0, 30% 2-0, 5% 3-0, 50% 4-0, 0% 5-0, 100% 6-0

    def forward(blocks):
        chain.sleep(1)
        chain.mine(blocks)

    start_block = len(chain)

    # DAY 0
    oceanutil.set_allocation(10000, allocate_addrs[0], CHAINID, alice)  # 100% at 0
    oceanutil.set_allocation(10000, allocate_addrs[0], CHAINID, bob)  # 100% at 0
    oceanutil.set_allocation(1000, allocate_addrs[0], CHAINID, karen)  # 10% at 0
    oceanutil.set_allocation(1000, allocate_addrs[0], CHAINID, james)  # 10% at 0

    forward(100)

    # DAY 1
    # Bob removes and re-adds 100%
    oceanutil.set_allocation(0, allocate_addrs[0], CHAINID, bob)  # 0% at 1
    oceanutil.set_allocation(10000, allocate_addrs[1], CHAINID, bob)  # 100% at 1

    # Karen allocates 10%
    oceanutil.set_allocation(1000, allocate_addrs[1], CHAINID, karen)  # 10% at 1

    # James allocates 20%
    oceanutil.set_allocation(2000, allocate_addrs[0], CHAINID, james)  # 20% at 1

    forward(100)

    # DAY 2
    # Bob removes and re-adds 100%
    oceanutil.set_allocation(0, allocate_addrs[1], CHAINID, bob)
    oceanutil.set_allocation(10000, allocate_addrs[2], CHAINID, bob)

    # Carol allocates 100%
    oceanutil.set_allocation(10000, allocate_addrs[2], CHAINID, carol)

    # Karen allocates 20%
    oceanutil.set_allocation(2000, allocate_addrs[2], CHAINID, karen)

    # James allocates 30%
    oceanutil.set_allocation(3000, allocate_addrs[0], CHAINID, james)
    forward(100)

    # DAY 3

    # Bob removes and re-adds 100%
    oceanutil.set_allocation(0, allocate_addrs[2], CHAINID, bob)
    oceanutil.set_allocation(10000, allocate_addrs[3], CHAINID, bob)

    # James allocates 5%
    oceanutil.set_allocation(500, allocate_addrs[0], CHAINID, james)

    forward(50)

    # DAY 3.5
    # Alice allocates 100%
    oceanutil.set_allocation(0, allocate_addrs[0], CHAINID, alice)
    oceanutil.set_allocation(10000, allocate_addrs[3], CHAINID, alice)

    forward(50)

    # DAY 4
    # Bob removes and re-adds 100%
    oceanutil.set_allocation(0, allocate_addrs[3], CHAINID, bob)
    oceanutil.set_allocation(10000, allocate_addrs[4], CHAINID, bob)

    # James allocates 50%
    oceanutil.set_allocation(5000, allocate_addrs[0], CHAINID, james)

    forward(100)

    # DAY 5

    # Bob removes and re-adds 100%
    oceanutil.set_allocation(0, allocate_addrs[4], CHAINID, bob)
    oceanutil.set_allocation(10000, allocate_addrs[5], CHAINID, bob)

    # James allocates 0%
    oceanutil.set_allocation(0, allocate_addrs[0], CHAINID, james)

    forward(100)

    # DAY 6
    # Bob removes and re-adds 100%
    oceanutil.set_allocation(0, allocate_addrs[5], CHAINID, bob)
    oceanutil.set_allocation(10000, allocate_addrs[6], CHAINID, bob)

    # Carol allocates 100%
    oceanutil.set_allocation(0, allocate_addrs[2], CHAINID, carol)
    oceanutil.set_allocation(10000, allocate_addrs[6], CHAINID, carol)

    # Karen allocates 100%
    oceanutil.set_allocation(0, allocate_addrs[0], CHAINID, karen)
    oceanutil.set_allocation(0, allocate_addrs[1], CHAINID, karen)
    oceanutil.set_allocation(0, allocate_addrs[2], CHAINID, karen)
    oceanutil.set_allocation(10000, allocate_addrs[6], CHAINID, karen)

    # James allocates 100%
    oceanutil.set_allocation(10000, allocate_addrs[0], CHAINID, james)

    # FIN
    forward(100)
    end_block = len(chain)

    # query
    rng = BlockRange(start_block, end_block, end_block - start_block, 42)

    allocations = None
    while True:
        try:
            allocations = queries.queryAllocations(rng, CHAINID)
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
    testToken = B.Simpletoken.deploy("CO2", "", 18, 1e26, {"from": god_acct})
    assert queries.symbol(testToken.address) == "CO2"

    testToken = B.Simpletoken.deploy("ASDASDASD", "", 18, 1e26, {"from": god_acct})
    assert queries.symbol(testToken.address) == "ASDASDASD"

    testToken = B.Simpletoken.deploy(
        "!@#$@!%$#^%$&~!@", "", 18, 1e26, {"from": god_acct}
    )
    assert queries.symbol(testToken.address) == "!@#$@!%$#^%$&~!@"


@enforce_types
def test_queryAquariusAssetNames():
    nft_dids = [
        "did:op:6637c63a7be53c4d7c6204b92e1508c928f9090ca822cec42782c8b1ec33bb2f",
        "did:op:fa0e8fa9550e8eb13392d6eeb9ba9f8111801b332c8d2345b350b3bc66b379d5",
        "did:op:ce3f161fb98c64a2ded37fd34e25f28343f2c88d0c8205242df9c621770d4b3b",
        # ↓ invalid, should return ""
        "did:op:4aa86d2c10f9a352ac9ec062122e318d66be6777e9a37c982e46aab144bc1cfa",
    ]

    expected_asset_names = [
        "OCEAN/USDT orderbook",
        "BTC/USDT orderbook",
        "DEX volume in details",
        "",
    ]
    assetNames = queries.queryAquariusAssetNames(nft_dids)
    print("assetNames", assetNames)
    assert len(assetNames) == 4

    for i in range(4):
        assert expected_asset_names.count(assetNames[nft_dids[i]]) == 1


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

    filtered_dids = queries._filterToAquariusAssets(nft_dids)

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

    filtered_dids = queries._filterDids(nft_dids)

    assert len(filtered_dids) == 3
    assert nft_dids[3] not in filtered_dids
    assert nft_dids[4] not in filtered_dids


@enforce_types
def test_filter_nft_vols_to_aquarius_assets():
    OCEAN_addr = oceanutil.OCEAN_address()
    nftaddrs = [
        "0x84d8fec21b295baf3bf5998e6d01c067b43d061a",
        "0x4b23ee226f61eecc6521697b9e5d96e4bdfb1d0c",
        "0x9723488dc1524849a82917a61a38bbe24a8219c1",
        OCEAN_addr,  # invalid, should filter out this one
    ]

    # these addresses are from polygon
    chain_id = 137

    # nftvols: dict of [basetoken_addr][nft_addr]:vol_amt
    nftvols = {}
    nftvols[OCEAN_addr] = {}
    for nftaddr in nftaddrs:
        nftvols[OCEAN_addr][nftaddr] = 1.0

    # filter out non-market assets
    nftvols_filtered = queries._filterNftvols(nftvols, chain_id)
    assert len(nftvols_filtered) == 1
    assert len(nftvols_filtered[OCEAN_addr]) == 3

    # match the addresses
    assert nftaddrs[0] in nftvols_filtered[OCEAN_addr]
    assert nftaddrs[1] in nftvols_filtered[OCEAN_addr]
    assert nftaddrs[2] in nftvols_filtered[OCEAN_addr]
    assert nftaddrs[3] not in nftvols_filtered[OCEAN_addr]


@enforce_types
def test_filter_out_purgatory():
    dids = [
        "did:op:01bf34f4e44e0c0549c34bf241940d397fca57aa6107b481789845464866d7b7",
        "did:op:01bf34f4e44e0c0549c34bf241940d397fca57aa6107b481789845464866d7b5",
    ]

    # filter out purgatory
    dids_filtered = queries._filterOutPurgatory(dids)
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
    nfts = [SimpleDataNft(137, addr, "TEST", "0x123") for addr in addrs]

    # filter
    nfts_filtered = queries._filterNftinfos(nfts)

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
    nfts = [SimpleDataNft(137, addr, "TEST", "0x123") for addr in addrs]

    nfts_marked = queries._markPurgatoryNfts(nfts)

    assert len(nfts_marked) == 3
    assert nfts_marked[1].is_purgatory is True


@enforce_types
def test_populate_nft_asset_names():
    nft_addr = "0xbff8242de628cd45173b71022648617968bd0962"
    nfts = [SimpleDataNft(137, nft_addr, "TEST", "0x123")]
    nfts = queries._populateNftAssetNames(nfts)

    assert nfts[0].name == "Take a Ballet Lesson"


@enforce_types
def test_SimpleDataNFT():
    # test attributes
    nft_addr = "0xBff8242de628cd45173b71022648617968bd0962"
    nft = SimpleDataNft(137, nft_addr, "dn1", "0x123AbC")
    assert nft.chain_id == 137
    assert nft.nft_addr == nft_addr.lower()
    assert nft.symbol == "DN1"
    assert nft.owner_addr == "0x123abc"
    assert nft.name == ""
    assert not nft.is_purgatory
    assert isinstance(nft.did, str)

    # test __eq__
    nft2 = SimpleDataNft(137, nft_addr, "Dn1", "0x123abC")
    assert nft == nft2

    nft3 = SimpleDataNft(137, nft_addr, "DN2", "0x123abc")
    assert nft != nft3

    # test __repr__
    repr1 = repr(nft)
    repr2 = f"SimpleDataNft(137, '{nft_addr.lower()}', 'DN1', '0x123abc', False, '')"
    assert repr1 == repr2

    # test set_name
    nft.set_name("nAmE1")
    assert nft.name == "nAmE1"
    assert "nAmE1" in repr(nft)

    # non-default args in constructor
    nft4 = SimpleDataNft(137, nft_addr, "DN2", "0x123abc", True, "namE2")
    assert nft4.is_purgatory
    assert nft4.name == "namE2"


@enforce_types
def test_filter_by_max_volume():
    nftvols = {"a": {"b": 1000}}
    swapvols = {"a": {"b": 100}}
    filteredvols = queries._filterbyMaxVolume(nftvols, swapvols)
    assert filteredvols["a"]["b"] == 100


@enforce_types
def test_process_single_delegation():
    # Prepare test data
    delegation = {
        "id": "x",
        "amount": "2.49315066506849681",
        "expireTime": "1813190400",
        "lockedAmount": "5",
        "timeLeftUnlock": 125798399,
        "delegator": {"id": "0x643c6de82231585d510c9fe915dcdef1c807121e"},
        "receiver": {"id": "0x37ba1e33f24bcd8cad3c083e1dc37c9f3d63d21d"},
    }
    balance_veocean_start = 5.0
    balance_veocean = 5.0
    unixEpochTime = 1687392001
    timeLeft = 125798500

    balance_veocean, delegation_amt, delegated_to = queries._process_delegation(
        delegation, balance_veocean, unixEpochTime, timeLeft
    )

    assert balance_veocean == balance_veocean_start - delegation_amt
    assert delegation_amt == approx(2.4931526)
    assert delegated_to == "0x37ba1e33f24bcd8cad3c083e1dc37c9f3d63d21d"


@enforce_types
def test_process_delegations():
    delegations = [
        {
            "id": "x",
            "amount": "2.49315066506849681",
            "expireTime": "1813190400",
            "lockedAmount": "5",
            "timeLeftUnlock": 125798399,
            "delegator": {"id": "0x643c6de82231585d510c9fe915dcdef1c807121e"},
            "receiver": {"id": "0x37ba1e33f24bcd8cad3c083e1dc37c9f3d63d21d"},
            "updates": [
                {
                    "timestamp": 1687392001,
                    "sender": "0x643c6de82231585d510c9fe915dcdef1c807121e",
                    "amount": "2.49315066506849681",
                    "type": 0,
                }
            ],
        },
        {
            "id": "x",
            "amount": "0.249315066506849681",
            "expireTime": "1813190400",
            "lockedAmount": "5",
            "timeLeftUnlock": 125798399,
            "delegator": {"id": "0x643c6de82231585d510c9fe915dcdef1c807121e"},
            "receiver": {"id": "0xcc34ca233293bdd9e50aca149d019a62fc881b90"},
            "updates": [
                {
                    "timestamp": 1687392001,
                    "sender": "0x643c6de82231585d510c9fe915dcdef1c807121e",
                    "amount": "0.249315066506849681",
                    "type": 0,
                }
            ],
        },
    ]

    balance_veocean_start = 5.0
    balance_veocean = 5.0
    unixEpochTime = 1687392001
    timeLeft = 125798500

    delegation_amts = []
    delegated_tos = []

    for delegation in delegations:
        balance_veocean, delegation_amt, delegated_to = queries._process_delegation(
            delegation, balance_veocean, unixEpochTime, timeLeft
        )
        delegation_amts.append(delegation_amt)
        delegated_tos.append(delegated_to)

    assert balance_veocean == balance_veocean_start - sum(delegation_amts)
    assert delegation_amts == approx([2.4931526, 0.2493151])
    assert delegated_tos == [
        "0x37ba1e33f24bcd8cad3c083e1dc37c9f3d63d21d",
        "0xcc34ca233293bdd9e50aca149d019a62fc881b90",
    ]


# ===========================================================================
# support functions


@enforce_types
def _lock(accts: list, lock_amt: float, lock_time: int):
    print("Lock...")
    lock_amt_wei = to_wei(lock_amt)
    for i, acct in enumerate(accts):
        s = str_with_wei(lock_amt_wei)
        print(f"  Lock {s} OCEAN on acct #{i+1}/{len(accts)}...")
        print(f"    chain.time() = {chain.time()}")
        print(f"    lock_time =    {lock_time}")
        print(f"    chain.time() <= lock_time? {chain.time() <= lock_time}")
        veOCEAN.checkpoint({"from": acct})
        OCEAN.approve(veOCEAN.address, lock_amt_wei, {"from": acct})
        veOCEAN.create_lock(lock_amt_wei, lock_time, {"from": acct})


@enforce_types
def _allocate(accts: list, assets: list):
    print("Allocate...")
    veAllocate = oceanutil.veAllocate()
    for i, (acct, asset) in enumerate(zip(accts, assets)):
        print(f"  Allocate veOCEAN on acct #{i+1}/{len(accts)}...")
        veAllocate.setAllocation(100, asset.nft, CHAINID, {"from": acct})


@enforce_types
def _fund_accts(accts_to_fund: list, amt_to_fund: float):
    print("Fund accts...")
    amt_to_fund_wei = to_wei(amt_to_fund)
    for i, acct in enumerate(accts_to_fund):
        print(f"  Create & fund account #{i+1}/{len(accts_to_fund)}...")
        god_acct.transfer(acct, "0.1 ether")
        OCEAN.transfer(acct, amt_to_fund_wei, {"from": god_acct})
        if CO2 is not None:
            CO2.transfer(acct, amt_to_fund_wei, {"from": god_acct})


@enforce_types
def _create_assets(n_assets: int) -> list:
    print("Create assets...")
    assets = []
    for i in range(n_assets):
        print(f"  Create asset #{i+1}/{n_assets}...")
        tup = oceanutil.create_data_nft_with_fre(god_acct, CO2)
        asset = SimpleAsset(tup)
        assets.append(asset)
    return assets


@enforce_types
def _clear_dir(csv_dir: str):
    """Remove the files inside csv_dir"""
    if csv_dir[-1] != "/":
        csv_dir += "/"
    cmd = f"rm {csv_dir}*"
    os.system(cmd)


@enforce_types
def setup_function():
    global god_acct, PREV, OCEAN, veOCEAN, chain
    networkutil.connect(CHAINID)
    chain = brownie.network.chain
    god_acct = brownie.network.accounts[0]
    oceanutil.record_dev_deployed_contracts()

    OCEAN = oceanutil.OCEAN_token()
    veOCEAN = oceanutil.veOCEAN()

    for envvar in ["ADDRESS_FILE", "SUBGRAPH_URI", "SECRET_SEED"]:
        PREV[envvar] = os.environ.get(envvar)

    os.environ["ADDRESS_FILE"] = ADDRESS_FILE
    os.environ["SUBGRAPH_URI"] = networkutil.chain_id_to_subgraph_uri(CHAINID)
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
