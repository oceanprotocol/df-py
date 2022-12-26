import time
import brownie
from enforce_typing import enforce_types
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
)
from util.constants import BROWNIE_PROJECT as B

accounts = None
ST = 0
FIN = 0


@enforce_types
def test_without_csvs():
    chainID = networkutil.DEV_CHAINID

    st, fin, n = ST, FIN, 25
    rng = blockrange.BlockRange(st, fin, n)

    (V0, SYM0) = query.queryNftvolsAndSymbols(rng, chainID)
    V = {chainID: V0}
    SYM = {chainID: SYM0}

    vebals, _, _ = query.queryVebalances(rng, chainID)
    allocs = query.queryAllocations(rng, chainID)
    stakes = allocations.allocsToStakes(allocs, vebals)

    R = {"OCEAN": 0.5, "H2O": 1.618}

    OCEAN_avail = 1e-4

    rewardsperlp, _ = calcrewards.calcRewards(stakes, V, SYM, R, OCEAN_avail)

    sum_ = sum(rewardsperlp[chainID].values())
    assert sum_ == pytest.approx(OCEAN_avail, OCEAN_avail / 1000.0), sum_


@enforce_types
def test_with_csvs(tmp_path):
    """
    Simulate these steps, with csvs in between
    1. dftool getrate
    2. dftool query
    3. dftool calc
    4. dftool dispense
    """
    chainID = networkutil.DEV_CHAINID
    csv_dir = str(tmp_path)

    st, fin, n = ST, FIN, 25
    rng = blockrange.BlockRange(st, fin, n)
    token_addr = oceanutil.OCEAN_address()

    # 1. simulate "dftool getrate"
    csvs.saveRateCsv("OCEAN", 0.25, csv_dir)
    csvs.saveRateCsv("H2O", 1.61, csv_dir)

    # 2. simulate "dftool query"
    (V0, SYM0) = query.queryNftvolsAndSymbols(rng, chainID)
    csvs.saveNftvolsCsv(V0, csv_dir, chainID)
    csvs.saveSymbolsCsv(SYM0, csv_dir, chainID)
    V0 = SYM0 = None  # ensure not used later

    vebals, locked_amt, unlock_time = query.queryVebalances(rng, chainID)
    allocs = query.queryAllocations(rng, chainID)
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

    sum_ = sum(rewardsperlp[chainID].values())
    assert sum_ == pytest.approx(OCEAN_avail, OCEAN_avail / 1000), sum_
    csvs.saveRewardsperlpCsv(rewardsperlp, csv_dir, "OCEAN")
    rewardsperlp = None  # ensure not used later

    # 4. simulate "dftool dispense"
    rewardsperlp = csvs.loadRewardsCsv(csv_dir, "OCEAN")
    dfrewards_addr = B.DFRewards.deploy({"from": accounts[0]}).address
    dispense.dispense(rewardsperlp[chainID], dfrewards_addr, token_addr, accounts[0])


@enforce_types
def setup_function():
    chainID = networkutil.DEV_CHAINID
    networkutil.connect(chainID)

    global accounts, ST, FIN
    accounts = brownie.network.accounts

    oceanutil.recordDevDeployedContracts()
    oceantestutil.fillAccountsWithOCEAN()

    OCEAN = oceanutil.OCEANtoken()
    ST = len(brownie.network.chain) - 1
    tups = oceantestutil.randomCreateDataNFTWithFREs(5, OCEAN, accounts)
    oceantestutil.randomConsumeFREs(tups, OCEAN)
    oceantestutil.randomLockAndAllocate(tups)
    FIN = len(brownie.network.chain) - 1

    brownie.network.chain.mine(20)
    brownie.network.chain.sleep(20)
    brownie.network.chain.mine(20)
    time.sleep(2)


@enforce_types
def teardown_function():
    networkutil.disconnect()
