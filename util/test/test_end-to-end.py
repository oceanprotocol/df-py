import time

import brownie
from enforce_typing import enforce_types
import numpy as np
import pytest

from util import (
    allocations,
    blockrange,
    calcrewards,
    csvs,
    dispense,
    oceanutil,
    oceantestutil,
    networkutil,
    query,
    tousd,
)
from util.cleancase import modStakes, modNFTvols
from util.constants import BROWNIE_PROJECT as B

CHAINID = networkutil.DEV_CHAINID

accounts = None
ST = 0
FIN = 0


@enforce_types
def test_end_to_end_main(tmp_path):
    _setup()
    _test_without_csvs()
    _test_with_csvs(tmp_path)


@enforce_types
def _test_without_csvs():
    print("test_end-to-end: _test_without_csvs: begin")

    st, fin, n = ST, FIN, 25
    rng = blockrange.BlockRange(st, fin, n)

    (V0, SYM0) = query.queryNftvolsAndSymbols(rng, CHAINID)
    V = {CHAINID: V0}
    SYM = {CHAINID: SYM0}

    vebals, _, _ = query.queryVebalances(rng, CHAINID)
    allocs = query.queryAllocations(rng, CHAINID)
    stakes = allocations.allocsToStakes(allocs, vebals)

    R = {"OCEAN": 0.5, "H2O": 1.618}

    OCEAN_avail = 1e-4

    rewardsperlp, _ = calcrewards.calcRewards(stakes, V, SYM, R, OCEAN_avail)

    sum_ = sum(rewardsperlp[CHAINID].values())
    assert sum_ == pytest.approx(OCEAN_avail, OCEAN_avail / 1000.0), sum_
    print("test_end-to-end: _test_without_csvs: done")


@enforce_types
def _test_with_csvs(tmp_path):
    """
    Simulate these steps, with csvs in between
    1. dftool getrate
    2. dftool volsym
    3. dftool calc
    4. dftool dispense
    """
    print("test_end-to-end: _test_with_csvs: begin")
    csv_dir = str(tmp_path)

    st, fin, n = ST, FIN, 25
    rng = blockrange.BlockRange(st, fin, n)
    token_addr = oceanutil.OCEAN_address()

    # 1. simulate "dftool getrate"
    csvs.saveRateCsv("OCEAN", 0.25, csv_dir)
    csvs.saveRateCsv("H2O", 1.61, csv_dir)

    # 2. simulate "dftool volsym"
    (V0, SYM0) = query.queryNftvolsAndSymbols(rng, CHAINID)
    csvs.saveNftvolsCsv(V0, csv_dir, CHAINID)
    csvs.saveSymbolsCsv(SYM0, csv_dir, CHAINID)
    V0 = SYM0 = None  # ensure not used later

    vebals, locked_amt, unlock_time = query.queryVebalances(rng, CHAINID)
    allocs = query.queryAllocations(rng, CHAINID)
    csvs.saveVebalsCsv(vebals, locked_amt, unlock_time, csv_dir)
    csvs.saveAllocationCsv(allocs, csv_dir)
    vebals = allocs = None  # ensure not used later

    # 3. simulate "dftool calc"
    R = csvs.loadRateCsvs(csv_dir)
    V = csvs.loadNftvolsCsvs(csv_dir)
    SYM = csvs.loadSymbolsCsvs(csv_dir)

    stakes = allocations.loadStakes(csv_dir)  # loads allocs & vebals, then *

    OCEAN_avail = 1e-4
    rewardsperlp, _ = calcrewards.calcRewards(stakes, V, SYM, R, OCEAN_avail)

    sum_ = sum(rewardsperlp[CHAINID].values())
    assert sum_ == pytest.approx(OCEAN_avail, OCEAN_avail / 1000), sum_
    csvs.saveRewardsperlpCsv(rewardsperlp, csv_dir, "OCEAN")
    rewardsperlp = None  # ensure not used later

    # 4. simulate "dftool dispense"
    rewardsperlp = csvs.loadRewardsCsv(csv_dir, "OCEAN")
    dfrewards_addr = B.DFRewards.deploy({"from": accounts[0]}).address
    dispense.dispense(rewardsperlp[CHAINID], dfrewards_addr, token_addr, accounts[0])

    print("test_end-to-end: _test_with_csvs: end")


@enforce_types
def _setup():
    print("test_end-to-end: _setup: begin")
    global accounts, ST, FIN

    networkutil.connect(CHAINID)
    accounts = brownie.network.accounts

    oceanutil.recordDevDeployedContracts()
    oceantestutil.fillAccountsWithOCEAN()

    OCEAN = oceanutil.OCEANtoken()
    ST = len(brownie.network.chain) - 1
    tups = oceantestutil.randomCreateDataNFTWithFREs(5, OCEAN, accounts)
    oceantestutil.randomConsumeFREs(tups, OCEAN)

    oceantestutil.randomLockAndAllocate(tups)

    # loop until graph query sees both consume & allocation, or timeout
    max_loops = 50
    for loop_i in range(max_loops):
        FIN = len(brownie.network.chain) - 1
        print(f"test_end-to-end: _setup: loop {loop_i} start")
        if _dataIsReady(OCEAN.address, ST, FIN):
            break
        if loop_i == (max_loops - 1):
            raise AssertionError("timeout")
        brownie.network.chain.sleep(10)
        brownie.network.chain.mine(10)
        time.sleep(2)

    print("test_end-to-end: _setup: done")


def _dataIsReady(OCEAN_addr, st, fin) -> bool:
    OCEAN_addr = OCEAN_addr.lower()
    n = 25
    if not _foundConsume(OCEAN_addr, st, fin):
        return False
    if not _foundAllocations(st, fin, n):
        return False

    rng = blockrange.BlockRange(st, fin, n)

    (V0, SYM0) = query.queryNftvolsAndSymbols(rng, CHAINID)
    nftvols = {CHAINID: V0}
    nftvols = modNFTvols(nftvols)

    symbols = {CHAINID: SYM0}

    vebals, _, _ = query.queryVebalances(rng, CHAINID)

    allocs = query.queryAllocations(rng, CHAINID)
    allocs = {CHAINID: allocs[str(CHAINID)]}  # workaround

    stakes = allocations.allocsToStakes(allocs, vebals)
    stakes = modStakes(stakes)

    rates = {"OCEAN": 0.5, "H2O": 1.618}

    nftvols_USD = tousd.nftvolsToUsd(nftvols, symbols, rates)

    S, _, _ = calcrewards._stakevolDictsToArrays(stakes, nftvols_USD)

    data_is_ready = np.sum(S) > 0.0
    return data_is_ready


@enforce_types
def _foundConsume(OCEAN_addr, st, fin):
    OCEAN_addr = OCEAN_addr.lower()
    vols = query._queryNftvolumes(st, fin, CHAINID)
    vols = query._filterNftvols(vols, CHAINID)
    if OCEAN_addr not in vols:
        return False
    if sum(vols[OCEAN_addr].values()) == 0:
        return False

    # all good
    return True


@enforce_types
def _foundAllocations(st, fin, n):
    rng = blockrange.BlockRange(st, fin, n)
    allocs = query.queryAllocations(rng, CHAINID)

    if CHAINID not in allocs:
        return False

    sum_allocs = 0.0
    for nft_addr in allocs[CHAINID]:
        for LP_addr in allocs[CHAINID][nft_addr]:
            sum_allocs += allocs[CHAINID][nft_addr][LP_addr]
    if sum_allocs == 0.0:
        return False

    # all good
    return True


@enforce_types
def teardown_function():
    networkutil.disconnect()
