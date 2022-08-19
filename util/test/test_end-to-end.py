import time
import brownie
from enforce_typing import enforce_types
import pytest

from util import (
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


@enforce_types
def test_without_csvs():
    chainID = networkutil.DEV_CHAINID

    st, fin, n = 1, len(brownie.network.chain), 25
    rng = blockrange.BlockRange(st, fin, n)

    (V0, A0, SYM0) = query.query_all(rng, chainID)
    vebals = query.getveBalances(rng, chainID)
    allocations = query.getAllocations(rng, chainID)
    R = {"OCEAN": 0.5, "H2O": 1.618}

    V, A, SYM = (
        {chainID: V0},
        {chainID: A0},
        {chainID: SYM0},
    )

    OCEAN_avail = 0.0001

    rewardsperlp, _ = calcrewards.calcRewards(
        allocations, vebals, V, A, SYM, R, OCEAN_avail, "OCEAN"
    )
    sum_ = sum(rewardsperlp[chainID].values())
    assert sum_ == pytest.approx(OCEAN_avail, 0.01), sum_


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

    st, fin, n = 1, len(brownie.network.chain), 25
    rng = blockrange.BlockRange(st, fin, n)
    token_addr = oceanutil.OCEAN_address()

    # 1. simulate "dftool getrate"
    csvs.saveRateCsv("OCEAN", 0.25, csv_dir)
    csvs.saveRateCsv("H2O", 1.61, csv_dir)

    # 2. simulate "dftool query"
    (V0, A0, SYM0) = query.query_all(rng, chainID)
    csvs.saveNFTvolsCsv(V0, csv_dir, chainID)
    csvs.saveApprovedCsv(A0, csv_dir, chainID)
    csvs.saveSymbolsCsv(SYM0, csv_dir, chainID)
    S0 = V0 = A0 = SYM0 = None  # ensure not used later

    vebals = query.getveBalances(rng, chainID)
    allocations = query.getAllocations(rng, chainID)
    csvs.saveVeOceanCsv(vebals, csv_dir)
    csvs.saveAllocationCsv(allocations, csv_dir)

    # 3. simulate "dftool calc"
    R = csvs.loadRateCsvs(csv_dir)
    allcs = csvs.loadAllocationCsvs(csv_dir)
    vebals = csvs.loadVeOceanCsv(csv_dir)
    V = csvs.loadNFTvolsCsvs(csv_dir)
    A = csvs.loadApprovedCsvs(csv_dir)
    SYM = csvs.loadSymbolsCsvs(csv_dir)

    OCEAN_avail = 0.0001
    rewardsperlp, _ = calcrewards.calcRewards(
        allcs, vebals, V, A, SYM, R, OCEAN_avail, "OCEAN"
    )
    sum_ = sum(rewardsperlp[chainID].values())
    assert sum_ == pytest.approx(OCEAN_avail, 0.01), sum_
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

    global accounts
    accounts = brownie.network.accounts

    oceanutil.recordDevDeployedContracts()
    oceantestutil.fillAccountsWithOCEAN()

    num_pools = 1
    OCEAN = oceanutil.OCEANtoken()
    oceantestutil.randomDeployTokensAndPoolsThenConsume(num_pools, OCEAN)
    oceantestutil.randomLockAndAllocate()

    brownie.network.chain.mine(20)
    brownie.network.chain.sleep(20)
    brownie.network.chain.mine(20)
    time.sleep(2)


@enforce_types
def teardown_function():
    networkutil.disconnect()
