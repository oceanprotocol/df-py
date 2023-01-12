# test_dftool1 - lightweight, doesn't need network
# test_dftool2 - uses network / brownie
import os
import time
import types

import brownie
from enforce_typing import enforce_types

from util import csvs, networkutil, oceanutil, oceantestutil
from util.base18 import fromBase18, toBase18
from util.constants import BROWNIE_PROJECT as B

accounts, PREV, DISPENSE_ACCT = None, None, None

CHAINID = networkutil.DEV_CHAINID
ADDRESS_FILE = networkutil.chainIdToAddressFile(networkutil.DEV_CHAINID)
ST = 0


@enforce_types
def test_query(tmp_path):
    CSV_DIR = str(tmp_path)

    # insert fake inputs: info onto the chain
    oceantestutil.fillAccountsWithOCEAN()
    time.sleep(2)

    # insert fake inputs: rate csv file
    csvs.saveRateCsv("OCEAN", 0.5, CSV_DIR)

    # main cmd
    FIN = "latest"
    NSAMP = 5

    cmd = f"./dftool volsym {ST} {FIN} {NSAMP} {CSV_DIR} {CHAINID}"
    os.system(cmd)

    # test result
    assert csvs.nftvolsCsvFilenames(CSV_DIR)
    assert csvs.symbolsCsvFilenames(CSV_DIR)


@enforce_types
def test_vebals(tmp_path):
    CSV_DIR = str(tmp_path)
    FIN = "latest"
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
def test_allocations(tmp_path):
    CSV_DIR = str(tmp_path)
    FIN = "latest"
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


@enforce_types
def test_dispense(tmp_path):
    # values used for inputs or main cmd
    global accounts
    accounts = brownie.network.accounts
    account1 = accounts[1]
    address1 = account1.address.lower()
    address2 = accounts[2].address.lower()
    CSV_DIR = str(tmp_path)
    TOT_OCEAN = 1000.0

    # accounts[0] has OCEAN. Ensure that dispensing account has some
    global DISPENSE_ACCT
    OCEAN = oceanutil.OCEANtoken()
    OCEAN.transfer(DISPENSE_ACCT, toBase18(TOT_OCEAN), {"from": accounts[0]})
    assert fromBase18(OCEAN.balanceOf(DISPENSE_ACCT.address)) == TOT_OCEAN

    # insert fake inputs: rewards csv, new dfrewards.sol contract
    rewards = {
        CHAINID: {address1: 400},
        "5": {address1: 300, address2: 300},
    }
    csvs.saveRewardsperlpCsv(rewards, CSV_DIR, "OCEAN")

    df_rewards = B.DFRewards.deploy({"from": accounts[0]})

    # main command
    CSV_DIR = str(tmp_path)
    DFREWARDS_ADDR = df_rewards.address
    TOKEN_ADDR = oceanutil.OCEAN_address()

    cmd = f"./dftool dispense_active {CSV_DIR} {CHAINID} {DFREWARDS_ADDR} {TOKEN_ADDR}"
    os.system(cmd)

    # test result
    assert df_rewards.claimable(address1, OCEAN.address) == toBase18(700.0)
    assert df_rewards.claimable(address2, OCEAN.address) == toBase18(300.0)


@enforce_types
def test_checkpoint_feedistributor():
    feeDistributor = oceanutil.FeeDistributor()
    timecursor_before = feeDistributor.time_cursor()
    brownie.network.chain.sleep(60 * 60 * 24 * 7)
    brownie.network.chain.mine()
    cmd = f"./dftool checkpoint_feedist {CHAINID}"
    os.system(cmd)

    timecursor_after = feeDistributor.time_cursor()

    assert timecursor_after > timecursor_before


@enforce_types
def setup_function():
    global accounts, PREV, DISPENSE_ACCT, ST

    networkutil.connect(CHAINID)
    ST = len(brownie.network.chain)
    accounts = brownie.network.accounts
    oceanutil.recordDevDeployedContracts()
    oceantestutil.fillAccountsWithOCEAN()

    PREV = types.SimpleNamespace()

    PREV.DFTOOL_KEY = os.environ.get("DFTOOL_KEY")
    DISPENSE_ACCT = brownie.network.accounts.add()
    os.environ["DFTOOL_KEY"] = DISPENSE_ACCT.private_key

    PREV.ADDRESS_FILE = os.environ.get("ADDRESS_FILE")
    os.environ["ADDRESS_FILE"] = networkutil.chainIdToAddressFile(CHAINID)

    PREV.SUBGRAPH_URI = os.environ.get("SUBGRAPH_URI")
    os.environ["SUBGRAPH_URI"] = networkutil.chainIdToSubgraphUri(CHAINID)

    os.environ["SECRET_SEED"] = "1234"

    OCEAN = oceanutil.OCEANtoken()
    tups = oceantestutil.randomCreateDataNFTWithFREs(8, OCEAN, accounts)
    oceantestutil.randomConsumeFREs(tups, OCEAN)
    oceantestutil.randomLockAndAllocate(tups)

    brownie.network.chain.mine(20)
    brownie.network.chain.sleep(20)
    brownie.network.chain.mine(20)
    time.sleep(2)


@enforce_types
def teardown_function():
    networkutil.disconnect()

    global PREV

    if PREV.DFTOOL_KEY is None:
        del os.environ["DFTOOL_KEY"]
    else:
        os.environ["DFTOOL_KEY"] = PREV.DFTOOL_KEY

    if PREV.ADDRESS_FILE is None:
        del os.environ["ADDRESS_FILE"]
    else:
        os.environ["ADDRESS_FILE"] = PREV.ADDRESS_FILE

    if PREV.SUBGRAPH_URI is None:
        del os.environ["SUBGRAPH_URI"]
    else:
        os.environ["SUBGRAPH_URI"] = PREV.SUBGRAPH_URI
