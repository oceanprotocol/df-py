import time
import types
import os
import brownie

from util import csvs, oceanutil, networkutil
from util.base18 import fromBase18, toBase18
from util.constants import BROWNIE_PROJECT as B
from util import oceantestutil

accounts = None

PREV = None
DISPENSE_ACCT = None

CHAINID = networkutil.DEV_CHAINID


@enforce_types
def test_query(tmp_path):
    # insert fake inputs: info onto the chain
    ADDRESS_FILE = os.environ.get("ADDRESS_FILE")
    oceantestutil.fillAccountsWithOCEAN()
    num_pools = 1
    OCEAN = oceanutil.OCEANtoken()
    oceantestutil.randomDeployTokensAndPoolsThenConsume(num_pools, OCEAN)
    time.sleep(2)

    # main cmd
    ST = 0
    FIN = "latest"
    NSAMP = 5
    CSV_DIR = str(tmp_path)

    cmd = f"./dftool query {ST} {FIN} {NSAMP} {CSV_DIR} {CHAINID}"
    os.system(cmd)

    # test result
    assert csvs.stakesCsvFilenames(CSV_DIR)
    assert csvs.poolvolsCsvFilenames(CSV_DIR)


@enforce_types
def test_getrate(tmp_path):
    # insert fake inputs:
    # <nothing to insert>

    # main cmd
    TOKEN_SYMBOL = "OCEAN"
    ST = "2022-01-01"
    FIN = "2022-02-02"
    CSV_DIR = str(tmp_path)

    cmd = f"./dftool getrate {TOKEN_SYMBOL} {ST} {FIN} {CSV_DIR}"
    os.system(cmd)

    # test result
    assert csvs.rateCsvFilenames(CSV_DIR)


@enforce_types
def test_calc(tmp_path):
    CSV_DIR = str(tmp_path)

    # insert fake inputs: csvs for stakes, poolvols, and rewards
    stakes_at_chain = {"OCEAN": {"pool_addra": {"lp_addr1": 1.0}}}
    csvs.saveStakesCsv(stakes_at_chain, CSV_DIR, CHAINID)

    poolvols_at_chain = {"OCEAN": {"pool_addra": 1.0}}
    csvs.savePoolvolsCsv(poolvols_at_chain, CSV_DIR, CHAINID)

    csvs.saveRateCsv("OCEAN", 0.50, CSV_DIR)

    # main cmd
    TOKEN_SYMBOL = "OCEAN"
    TOT_TOKEN = 1000.0

    cmd = f"./dftool calc {CSV_DIR} {TOT_TOKEN} {TOKEN_SYMBOL}"
    os.system(cmd)

    # test result
    rewards_csv = csvs.rewardsCsvFilename(CSV_DIR, TOKEN_SYMBOL)
    assert os.path.exists(rewards_csv)


@enforce_types
def test_dispense(tmp_path):
    # values used for inputs or main cmd
    accounts = brownie.network.accounts
    account1 = accounts[1]
    address1 = account1.address.lower()
    CSV_DIR = str(tmp_path)
    TOKEN_SYMBOL = "OCEAN"
    TOT_TOKEN = 1000.0

    # accounts[0] has OCEAN. Ensure that dispensing account has some
    global DISPENSE_ACCT
    ADDRESS_FILE = os.environ.get("ADDRESS_FILE")
    OCEAN = oceanutil.OCEANtoken()
    OCEAN.transfer(DISPENSE_ACCT, toBase18(TOT_TOKEN), {"from": accounts[0]})
    assert fromBase18(OCEAN.balanceOf(DISPENSE_ACCT.address)) == TOT_TOKEN

    # insert fake inputs: rewards csv, new dfrewards.sol contract
    rewards = {CHAINID: {address1: TOT_TOKEN}}
    csvs.saveRewardsCsv(rewards, CSV_DIR, TOKEN_SYMBOL)

    df_rewards = B.DFRewards.deploy({"from": accounts[0]})

    # main command
    CSV_DIR = str(tmp_path)
    DFREWARDS_ADDR = df_rewards.address
    TOKEN_ADDR = oceanutil.OCEAN_address()

    cmd = f"./dftool dispense {CSV_DIR} {CHAINID} {DFREWARDS_ADDR} {TOKEN_ADDR}"
    os.system(cmd)

    # test result
    assert df_rewards.claimable(address1, OCEAN.address)


@enforce_types
def setup_module():
    networkutil.connect(CHAINID)
    global accounts
    accounts = brownie.network.accounts
    oceanutil.recordDevDeployedContracts()
    
    global PREV, DISPENSE_ACCT

    PREV = types.SimpleNamespace()

    PREV.DFTOOL_KEY = os.environ.get("DFTOOL_KEY")
    DISPENSE_ACCT = brownie.network.accounts.add()
    os.environ["DFTOOL_KEY"] = DISPENSE_ACCT.private_key

    PREV.ADDRESS_FILE = os.environ.get("ADDRESS_FILE")
    os.environ["ADDRESS_FILE"] = networkutil.chainIdToAddressFile(CHAINID)

    PREV.SUBGRAPH_URI = os.environ.get("SUBGRAPH_URI")
    os.environ["SUBGRAPH_URI"] = networkutil.chainIdToSubgraphUri(CHAINID)


@enforce_types
def teardown_module():
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



