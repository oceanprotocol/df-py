import contextlib
import datetime
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import brownie
import pytest
from enforce_typing import enforce_types

from df_py.predictoor.csvs import (
    load_predictoor_data_csv,
    load_predictoor_rewards_csv,
    predictoor_data_csv_filename,
    predictoor_rewards_csv_filename,
    save_predictoor_rewards_csv,
)
from df_py.predictoor.predictoor_testutil import create_mock_responses
from df_py.util import dftool_module, networkutil, oceantestutil, oceanutil
from df_py.util.base18 import from_wei, to_wei
from df_py.util.constants import BROWNIE_PROJECT as B
from df_py.util.dftool_module import do_predictoor_data
from df_py.volume import csvs

PREV, DFTOOL_ACCT = {}, None

CHAINID = networkutil.DEV_CHAINID
ADDRESS_FILE = networkutil.chainIdToAddressFile(CHAINID)


@contextlib.contextmanager
def sysargs_context(arguments):
    old_sys_argv = sys.argv
    sys.argv = arguments
    yield
    sys.argv = old_sys_argv


@enforce_types
def test_calc(tmp_path):
    CSV_DIR = str(tmp_path)
    OCEAN_addr = oceanutil.OCEAN_address()

    # insert fake csvs
    allocations = {CHAINID: {"0xnft_addra": {"0xlp_addr1": 1.0}}}
    csvs.save_allocation_csv(allocations, CSV_DIR)

    nftvols_at_chain = {OCEAN_addr: {"0xnft_addra": 1.0}}
    csvs.save_nftvols_csv(nftvols_at_chain, CSV_DIR, CHAINID)

    owners_at_chain = {"0xnft_addra": "0xlp_addr1"}
    csvs.save_owners_csv(owners_at_chain, CSV_DIR, CHAINID)

    vebals = {"0xlp_addr1": 1.0}
    locked_amt = {"0xlp_addr1": 10.0}
    unlock_time = {"0xlp_addr1": 1}
    csvs.save_vebals_csv(vebals, locked_amt, unlock_time, CSV_DIR)

    symbols_at_chain = {OCEAN_addr: "OCEAN"}
    csvs.save_symbols_csv(symbols_at_chain, CSV_DIR, CHAINID)

    csvs.save_rate_csv("OCEAN", 0.50, CSV_DIR)

    # main cmd
    TOT_OCEAN = 1000.0
    START_DATE = "2023-02-02"  # Only substream is volume DF
    cmd = f"./dftool calc volume {CSV_DIR} {TOT_OCEAN} --START_DATE {START_DATE}"
    os.system(cmd)

    # test result
    rewards_csv = csvs.volume_rewards_csv_filename(CSV_DIR)
    assert os.path.exists(rewards_csv)


@enforce_types
def test_predictoor_data(tmp_path):
    CSV_DIR = str(tmp_path)

    sys_argv = [
        "dftool",
        "predictoor_data",
        "0",
        "latest",
        CSV_DIR,
        str(CHAINID),
        "--RETRIES=1",
    ]

    mock_query_response, users, stats = create_mock_responses(100)

    with sysargs_context(sys_argv):
        with patch("df_py.predictoor.queries.submitQuery") as mock_submitQuery:
            mock_submitQuery.side_effect = mock_query_response
            do_predictoor_data()

    # test result
    predictoor_data_csv = predictoor_data_csv_filename(CSV_DIR)
    assert os.path.exists(predictoor_data_csv)

    predictoors = load_predictoor_data_csv(CSV_DIR)
    for user in users:
        if stats[user]["total"] == 0:
            assert user not in predictoors
            continue
        user_total = stats[user]["total"]
        user_correct = stats[user]["correct"]
        assert predictoors[user].prediction_count == user_total
        assert predictoors[user].correct_prediction_count == user_correct
        assert predictoors[user].accuracy == user_correct / user_total


@enforce_types
def test_calc_predictoor_substream(tmp_path):
    CSV_DIR = str(tmp_path)

    csv_template = """predictoor_addr,accuracy,n_preds,n_correct_preds
0x0000000000000000000000000000000000000001,0.5,1818,909
0x1000000000000000000000000000000000000001,0.5,234,909
0x2000000000000000000000000000000000000001,0.5,1818,909
0x3000000000000000000000000000000000000001,0.5,754,909
0x4000000000000000000000000000000000000001,0.5,1818,909
"""
    predictoor_data_csv = predictoor_data_csv_filename(CSV_DIR)
    with open(predictoor_data_csv, "w") as f:
        f.write(csv_template)

    # main cmd

    # TEST WITH TOT_OCEAN > 0
    TOT_OCEAN = 1000.0
    ST = "2023-03-16"  # first week of df main
    cmd = f"./dftool calc predictoor {CSV_DIR} {TOT_OCEAN} --START_DATE {ST}"
    os.system(cmd)

    # test result
    rewards_csv = predictoor_rewards_csv_filename(CSV_DIR)
    assert os.path.exists(rewards_csv)

    # get total reward amount
    rewards = load_predictoor_rewards_csv(CSV_DIR)
    total_reward = sum(rewards.values())
    assert total_reward == 1000.0

    # delete rewards csv
    os.remove(rewards_csv)

    # TEST WITH TOT_OCEAN = 0, DATE WITH NONZERO REWARDS
    TOT_OCEAN = 0
    ST = "2042-03-16"  # some date where predictoor rewards are nonzero
    cmd = f"./dftool calc predictoor {CSV_DIR} {TOT_OCEAN} --START_DATE {ST}"
    os.system(cmd)

    # test result
    rewards_csv = predictoor_rewards_csv_filename(CSV_DIR)
    assert os.path.exists(rewards_csv)
    rewards = load_predictoor_rewards_csv(CSV_DIR)
    total_reward = sum(rewards.values())
    assert total_reward > 0

    # delete rewards csv
    os.remove(rewards_csv)

    # TEST WITH TOT_OCEAN = 0, DATE WITH ZERO REWARDS
    TOT_OCEAN = 0
    ST = "2023-01-01"  # some date where predictoor rewards are zero
    cmd = f"./dftool calc predictoor {CSV_DIR} {TOT_OCEAN} --START_DATE {ST}"
    os.system(cmd)

    # test result
    rewards_csv = predictoor_rewards_csv_filename(CSV_DIR)
    assert os.path.exists(rewards_csv)
    rewards = load_predictoor_rewards_csv(CSV_DIR)
    total_reward = sum(rewards.values())
    assert total_reward == 0


@enforce_types
def test_calc_without_amount(tmp_path):
    CSV_DIR = str(tmp_path)
    OCEAN_addr = oceanutil.OCEAN_address()

    # insert fake csvs
    allocations = {CHAINID: {"0xnft_addra": {"0xlp_addr1": 1.0}}}
    csvs.save_allocation_csv(allocations, CSV_DIR)

    nftvols_at_chain = {OCEAN_addr: {"0xnft_addra": 1e10}}
    csvs.save_nftvols_csv(nftvols_at_chain, CSV_DIR, CHAINID)

    owners_at_chain = {"0xnft_addra": "0xlp_addr1"}
    csvs.save_owners_csv(owners_at_chain, CSV_DIR, CHAINID)

    vebals = {"0xlp_addr1": 1e8}
    locked_amt = {"0xlp_addr1": 10.0}
    unlock_time = {"0xlp_addr1": 1}
    csvs.save_vebals_csv(vebals, locked_amt, unlock_time, CSV_DIR)

    symbols_at_chain = {OCEAN_addr: "OCEAN"}
    csvs.save_symbols_csv(symbols_at_chain, CSV_DIR, CHAINID)

    csvs.save_rate_csv("OCEAN", 0.50, CSV_DIR)

    # main cmd
    TOT_OCEAN = 0
    ST = "2023-03-16"  # first week of df main
    cmd = f"./dftool calc volume {CSV_DIR} {TOT_OCEAN} --START_DATE {ST}"
    os.system(cmd)

    # test result
    rewards_csv = csvs.volume_rewards_csv_filename(CSV_DIR)
    assert os.path.exists(rewards_csv)

    # get total reward amount
    rewards = csvs.load_volume_rewards_csv(CSV_DIR)
    total_reward = 0
    for _, addrs in rewards.items():
        for _, reward in addrs.items():
            total_reward += reward
    assert total_reward == 75000.0


@enforce_types
def test_dispense(tmp_path):
    # values used for inputs or main cmd
    accounts = brownie.network.accounts
    address1 = accounts[1].address.lower()
    address2 = accounts[2].address.lower()
    CSV_DIR = str(tmp_path)
    TOT_OCEAN = 1000.0

    # accounts[0] has OCEAN. Ensure that ispensing account has some
    global DFTOOL_ACCT
    OCEAN = oceanutil.OCEANtoken()
    OCEAN.transfer(DFTOOL_ACCT, to_wei(TOT_OCEAN), {"from": accounts[0]})
    assert from_wei(OCEAN.balanceOf(DFTOOL_ACCT.address)) == TOT_OCEAN

    # insert fake inputs: rewards csv, new dfrewards.sol contract
    rewards = {
        CHAINID: {address1: 400},
        "5": {address1: 300, address2: 100},
    }
    csvs.save_volume_rewards_csv(rewards, CSV_DIR)
    save_predictoor_rewards_csv({}, CSV_DIR)

    df_rewards = B.DFRewards.deploy({"from": accounts[0]})

    # main command
    CSV_DIR = str(tmp_path)
    DFREWARDS_ADDR = df_rewards.address
    OCEAN_ADDR = oceanutil.OCEAN_address()

    sys_argv = [
        "dftool",
        "dispense_active",
        CSV_DIR,
        str(CHAINID),
        f"--DFREWARDS_ADDR={DFREWARDS_ADDR}",
        f"--TOKEN_ADDR={OCEAN_ADDR}",
    ]

    # Mock the connection, otherwise the test setup clashes with
    # the implementation itself, and cleans up the contracts.
    # Either way, we are already connected to ganache through tests.

    with patch.object(dftool_module.networkutil, "connect"):
        with sysargs_context(sys_argv):
            dftool_module.do_dispense_active()

    # test result
    assert from_wei(df_rewards.claimable(address1, OCEAN_ADDR)) == 700.0
    assert from_wei(df_rewards.claimable(address2, OCEAN_ADDR)) == 100.0


@enforce_types
def test_manyrandom():
    sys_argv = [
        "dftool",
        "manyrandom",
        str(CHAINID),
    ]

    with sysargs_context(sys_argv):
        dftool_module.do_manyrandom()

    # different chain id will fail
    sys_argv = ["dftool", "manyrandom", "3"]

    with pytest.raises(SystemExit):
        with sysargs_context(sys_argv):
            dftool_module.do_manyrandom()


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
def test_calc_passive(tmp_path):
    accounts = []
    account0 = brownie.network.accounts[0]
    OCEAN = oceanutil.OCEANtoken()
    OCEAN_lock_amt = to_wei(10.0)
    S_PER_WEEK = 604800
    chain = brownie.network.chain
    feeDistributor = oceanutil.FeeDistributor()
    veOCEAN = oceanutil.veOCEAN()
    CSV_DIR = str(tmp_path)
    unlock_time = chain.time() + S_PER_WEEK * 10

    for _ in range(2):
        acc = brownie.network.accounts.add()
        account0.transfer(acc, to_wei(0.1))
        OCEAN.transfer(acc, OCEAN_lock_amt, {"from": account0})
        # create lock
        OCEAN.approve(veOCEAN, OCEAN_lock_amt, {"from": acc})
        veOCEAN.create_lock(OCEAN_lock_amt, unlock_time, {"from": acc})
        accounts.append(acc)

    for _ in range(3):
        OCEAN.transfer(
            feeDistributor.address,
            to_wei(1000.0),
            {"from": brownie.accounts[0]},
        )
        chain.sleep(S_PER_WEEK)
        chain.mine()
        feeDistributor.checkpoint_token({"from": brownie.accounts[0]})
        feeDistributor.checkpoint_total_supply({"from": brownie.accounts[0]})

    fake_vebals = {}
    locked_amt = {}
    unlock_times = {}
    for acc in accounts:
        fake_vebals[acc.address] = from_wei(veOCEAN.balanceOf(acc.address))
        locked_amt[acc.address] = OCEAN_lock_amt
        unlock_times[acc.address] = unlock_time
    csvs.save_vebals_csv(fake_vebals, locked_amt, unlock_times, CSV_DIR, False)
    date = chain.time() // S_PER_WEEK * S_PER_WEEK
    date = datetime.datetime.utcfromtimestamp(date).strftime("%Y-%m-%d")
    cmd = f"./dftool calculate_passive {CHAINID} {date} {CSV_DIR}"
    os.system(cmd)

    filename = csvs.passive_csv_filename(CSV_DIR)
    assert os.path.exists(filename)

    # number of lines must be >=3
    with open(filename, "r") as f:
        lines = f.readlines()
        assert len(lines) >= 3


def test_initdevwallets():
    account8 = brownie.network.accounts[8]
    account9 = brownie.network.accounts[9]

    OCEAN = oceanutil.OCEANtoken()
    OCEAN.transfer(account8, OCEAN.balanceOf(account9.address), {"from": account9})

    assert from_wei(OCEAN.balanceOf(account9.address)) == 0.0

    sys_argv = ["dftool", "initdevwallets", str(networkutil.DEV_CHAINID)]

    # Mock the connection, otherwise the test setup clashes with
    # the implementation itself, and cleans up the contracts.
    # Either way, we are already connected to ganache through tests.
    with patch.object(dftool_module.networkutil, "connect"):
        with sysargs_context(sys_argv):
            dftool_module.do_initdevwallets()

    assert from_wei(OCEAN.balanceOf(account9.address)) > 1.0

    # different chain id will fail
    sys_argv = ["dftool", "initdevwallets", "3"]

    with pytest.raises(SystemExit):
        with sysargs_context(sys_argv):
            dftool_module.do_initdevwallets()


def test_volsym(tmp_path):
    CSV_DIR = str(tmp_path)

    sys_argv = [
        "dftool",
        "volsym",
        "2023-03-16",  # first week of df main
        "latest",
        "10",
        CSV_DIR,
        str(networkutil.DEV_CHAINID),
    ]

    # rates does not exist
    with pytest.raises(SystemExit):
        with sysargs_context(sys_argv):
            dftool_module.do_volsym()

    rate_file = os.path.join(tmp_path, "rate-test.csv")
    Path(rate_file).write_text("")

    with patch.object(dftool_module, "retryFunction") as mock:
        with sysargs_context(sys_argv):
            mock.return_value = ({}, {}, {})
            dftool_module.do_volsym()

    assert os.path.exists(os.path.join(CSV_DIR, "nftvols-8996.csv"))
    assert os.path.exists(os.path.join(CSV_DIR, "owners-8996.csv"))
    assert os.path.exists(os.path.join(CSV_DIR, "symbols-8996.csv"))

    os.remove(os.path.join(CSV_DIR, "nftvols-8996.csv"))
    os.remove(os.path.join(CSV_DIR, "owners-8996.csv"))
    os.remove(os.path.join(CSV_DIR, "symbols-8996.csv"))

    del os.environ["ADDRESS_FILE"]
    # rates does not exist
    with pytest.raises(SystemExit):
        with sysargs_context(sys_argv):
            dftool_module.do_volsym()

    os.environ["ADDRESS_FILE"] = ADDRESS_FILE
    del os.environ["SECRET_SEED"]
    # rates does not exist
    with pytest.raises(SystemExit):
        with sysargs_context(sys_argv):
            dftool_module.do_volsym()

    os.environ["SECRET_SEED"] = "1234"


def test_nftinfo(tmp_path):
    CSV_DIR = str(tmp_path)

    sys_argv = [
        "dftool",
        "nftinfo",
        CSV_DIR,
        str(networkutil.DEV_CHAINID),
    ]

    with sysargs_context(sys_argv):
        with patch.object(dftool_module, "retryFunction") as mock:
            mock.return_value = []
            dftool_module.do_nftinfo()

    assert os.path.exists(os.path.join(CSV_DIR, "nftinfo_8996.csv"))


def test_allocations(tmp_path):
    CSV_DIR = str(tmp_path)

    sys_argv = [
        "dftool",
        "allocations",
        "0",
        "latest",
        "10",
        CSV_DIR,
        str(networkutil.DEV_CHAINID),
    ]

    with sysargs_context(sys_argv):
        with patch.object(dftool_module, "retryFunction") as mock:
            mock.return_value = {}
            dftool_module.do_allocations()

    assert os.path.exists(os.path.join(CSV_DIR, "allocations.csv"))

    # file already exists
    with pytest.raises(SystemExit):
        with sysargs_context(sys_argv):
            dftool_module.do_allocations()


def test_vebals(tmp_path):
    CSV_DIR = str(tmp_path)

    sys_argv = [
        "dftool",
        "vebals",
        "0",
        "latest",
        "10",
        CSV_DIR,
        str(networkutil.DEV_CHAINID),
    ]

    with sysargs_context(sys_argv):
        with patch.object(dftool_module, "retryFunction") as mock:
            mock.return_value = ({}, {}, {})
            dftool_module.do_vebals()

    assert os.path.exists(os.path.join(CSV_DIR, "vebals.csv"))


def test_df_strategies():
    sys_argv = [
        "dftool",
        "newdfrewards",
        str(networkutil.DEV_CHAINID),
    ]

    with sysargs_context(sys_argv):
        dftool_module.do_newdfrewards()

    sys_argv = [
        "dftool",
        "newdfstrategy",
        str(networkutil.DEV_CHAINID),
        "0x0",
        "testStrategy",
    ]

    with sysargs_context(sys_argv):
        with patch.object(dftool_module, "B"):
            dftool_module.do_newdfstrategy()

    sys_argv = [
        "dftool",
        "addstrategy",
        str(networkutil.DEV_CHAINID),
        "0x0",
        "0x0",
    ]

    with sysargs_context(sys_argv):
        with patch.object(dftool_module, "B") as mock_B:
            mock_df = Mock()
            mock_tx = Mock()
            mock_tx.events.keys.return_value = ["StrategyAdded"]
            mock_df.addStrategy.return_value = mock_tx
            mock_B.DFRewards.at.return_value = mock_df
            dftool_module.do_addstrategy()

    sys_argv = [
        "dftool",
        "retirestrategy",
        str(networkutil.DEV_CHAINID),
        "0x0",
        "0x0",
    ]

    with sysargs_context(sys_argv):
        with patch.object(dftool_module, "B") as mock_B:
            mock_df = Mock()
            mock_tx = Mock()
            mock_tx.events.keys.return_value = ["StrategyRetired"]
            mock_df.retireStrategy.return_value = mock_tx
            mock_B.DFRewards.at.return_value = mock_df
            dftool_module.do_retirestrategy()


def test_getrate(tmp_path):
    CSV_DIR = str(tmp_path)

    sys_argv = [
        "dftool",
        "getrate",
        "OCEAN",
        "0",
        "latest",
        CSV_DIR,
    ]

    with sysargs_context(sys_argv):
        with patch.object(dftool_module, "retryFunction") as mock:
            mock.return_value = 100.0
            dftool_module.do_getrate()

    assert os.path.exists(os.path.join(CSV_DIR, "rate-OCEAN.csv"))


def test_compile():
    sys_argv = ["dftool", "compile"]

    with sysargs_context(sys_argv):
        with patch("os.system"):
            dftool_module.do_compile()


def test_mine():
    sys_argv = ["dftool", "mine", "10"]

    with sysargs_context(sys_argv):
        dftool_module.do_mine()

    sys_argv = ["dftool", "mine", "10", "--TIMEDELTA=100"]

    with sysargs_context(sys_argv):
        dftool_module.do_mine()


def test_new_functions():
    sys_argv = ["dftool", "newacct", str(networkutil.DEV_CHAINID)]

    with sysargs_context(sys_argv):
        dftool_module.do_newacct()

    sys_argv = ["dftool", "newtoken", str(networkutil.DEV_CHAINID)]

    with sysargs_context(sys_argv):
        dftool_module.do_newtoken()

    sys_argv = ["dftool", "newVeOcean", str(networkutil.DEV_CHAINID), "0x0"]

    with sysargs_context(sys_argv):
        with patch.object(dftool_module, "B") as mock_B:
            mock_token = Mock()
            mock_token.symbol.return_value = "SYMB"
            mock_token.address = "0x0"
            mock_token.token = ""
            mock_B.veOcean.deploy.return_value = mock_token
            dftool_module.do_newVeOcean()

    sys_argv = ["dftool", "newVeAllocate", str(networkutil.DEV_CHAINID)]

    with sysargs_context(sys_argv):
        dftool_module.do_newVeAllocate()


def test_acctinfo():
    sys_argv = ["dftool", "acctinfo", str(networkutil.DEV_CHAINID), "1"]

    # Mock the connection, otherwise the test setup clashes with
    # the implementation itself, and cleans up the contracts.
    # Either way, we are already connected to ganache through tests.

    with patch.object(dftool_module.networkutil, "connect"):
        with sysargs_context(sys_argv):
            dftool_module.do_acctinfo()

    OCEAN_addr = oceanutil.OCEAN_address()
    sys_argv = [
        "dftool",
        "acctinfo",
        str(networkutil.DEV_CHAINID),
        "1",
        f"--TOKEN_ADDR={OCEAN_addr}",
    ]

    # Mock the connection, otherwise the test setup clashes with
    # the implementation itself, and cleans up the contracts.
    # Either way, we are already connected to ganache through tests.

    with patch.object(dftool_module.networkutil, "connect"):
        with sysargs_context(sys_argv):
            dftool_module.do_acctinfo()


def test_chaininfo():
    sys_argv = ["dftool", "chaininfo", str(networkutil.DEV_CHAINID)]

    with sysargs_context(sys_argv):
        dftool_module.do_chaininfo()


def test_dispense_passive():
    sys_argv = [
        "dftool",
        "dispense_passive",
        str(networkutil.DEV_CHAINID),
        "0",
        "2023-02-02",
    ]

    with patch.object(dftool_module, "retryFunction"):
        with sysargs_context(sys_argv):
            dftool_module.do_dispense_passive()


def test_calculate_passive(tmp_path):
    CSV_DIR = str(tmp_path)
    sys_argv = [
        "dftool",
        "calculate_passive",
        str(networkutil.DEV_CHAINID),
        "2023-02-02",
        CSV_DIR,
    ]

    with pytest.raises(SystemExit):
        with sysargs_context(sys_argv):
            dftool_module.do_calculate_passive()

    vebals_file = os.path.join(tmp_path, "vebals_realtime.csv")
    Path(vebals_file).write_text("LP_addr,balance,locked_amt,unlock_time")

    with patch.object(dftool_module, "queries") as mock:
        mock.queryPassiveRewards.return_value = {}, {}
        with sysargs_context(sys_argv):
            dftool_module.do_calculate_passive()


@enforce_types
def setup_function():
    global PREV, DFTOOL_ACCT

    networkutil.connect(CHAINID)
    accounts = brownie.network.accounts
    oceanutil.recordDevDeployedContracts()
    oceantestutil.fillAccountsWithOCEAN()

    DFTOOL_ACCT = accounts.add()
    accounts[0].transfer(DFTOOL_ACCT, to_wei(0.001))

    for envvar in [
        "DFTOOL_KEY",
        "ADDRESS_FILE",
        "SUBGRAPH_URI",
        "SECRET_SEED",
        "WEB3_INFURA_PROJECT_ID",
    ]:
        PREV[envvar] = os.environ.get(envvar)

    os.environ["DFTOOL_KEY"] = DFTOOL_ACCT.private_key
    os.environ["ADDRESS_FILE"] = ADDRESS_FILE
    os.environ["SUBGRAPH_URI"] = networkutil.chainIdToSubgraphUri(CHAINID)
    os.environ["SECRET_SEED"] = "1234"
    os.environ["WEB3_INFURA_PROJECT_ID"] = "9aa3d95b3bc440fa88ea12eaa4456161"


@enforce_types
def teardown_function():
    networkutil.disconnect()

    global PREV
    for envvar, envval in PREV.items():
        if envval is None:
            del os.environ[envvar]
        else:
            os.environ[envvar] = envval
    PREV = {}
