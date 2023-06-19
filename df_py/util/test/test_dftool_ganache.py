import contextlib
import datetime
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import brownie
import pytest
from enforce_typing import enforce_types

from df_py.challenge.csvs import challenge_data_csv_filename, load_challenge_rewards_csv
from df_py.predictoor.csvs import (
    load_predictoor_data_csv,
    load_predictoor_rewards_csv,
    predictoor_data_csv_filename,
    predictoor_rewards_csv_filename,
)
from df_py.predictoor.predictoor_testutil import create_mock_responses
from df_py.util import dftool_module, networkutil, oceantestutil, oceanutil
from df_py.util.base18 import from_wei, to_wei
from df_py.util.constants import BROWNIE_PROJECT as B
from df_py.util.dftool_module import do_predictoor_data
from df_py.util.getrate import getrate
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


class MockArgs:
    def __init__(self, dictionary):
        for k, v in dictionary.items():
            setattr(self, k, v)


@enforce_types
def test_predictoor_data(tmp_path):
    CSV_DIR = str(tmp_path)
    testargs = MockArgs(
        {
            "command": "predictoor_data",
            "ST": 0,
            "FIN": "latest",
            "CSV_DIR": CSV_DIR,
            "CHAINID": CHAINID,
            "RETRIES": 1,
        }
    )
    mock_query_response, users, stats = create_mock_responses(100)

    with patch("argparse.ArgumentParser.parse_args") as mock_args:
        mock_args.return_value = testargs
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
def test_calc_challenge_substream(tmp_path):
    CSV_DIR = str(tmp_path)

    csv_template = """from_addr,nft_addr,nmse
0x0000000000000000000000000000000000000001,0x01,0.1
0x1000000000000000000000000000000000000001,0x02,0.122
0x2000000000000000000000000000000000000001,0x03,0.3
0x3000000000000000000000000000000000000001,0x04,0.8
0x4000000000000000000000000000000000000001,0x05,0.88
"""
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    safe_limit = 1300 * (1 / getrate("OCEAN", today, today))

    challenge_data_csv = challenge_data_csv_filename(CSV_DIR)
    with open(challenge_data_csv, "w") as f:
        f.write(csv_template)

    CSV_DIR = str(tmp_path)

    with sysargs_context(["dftool", "calc", "challenge", CSV_DIR, str(safe_limit)]):
        dftool_module.do_calc()

    rewards = load_challenge_rewards_csv(CSV_DIR)
    assert len(rewards) == 3
    assert rewards["0x0000000000000000000000000000000000000001"] > 0

    # not enough available tokens
    with sysargs_context(["dftool", "calc", "challenge", CSV_DIR, "750"]):
        with pytest.raises(SystemExit):
            dftool_module.do_calc()

    # no rewards case:
    csv_template = "from_addr,nft_addr,nmse"

    with open(challenge_data_csv, "w") as f:
        f.write(csv_template)

    with sysargs_context(["dftool", "calc", "challenge", CSV_DIR, str(safe_limit)]):
        with pytest.raises(SystemExit):
            dftool_module.do_calc()


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
    ST = "2023-03-16"  # first week of df main
    sys_args = ["dftool", "calc", "volume", CSV_DIR, "0", f"--START_DATE={ST}"]

    with patch("df_py.util.dftool_module.recordDeployedContracts") as mock:
        with patch(
            "df_py.util.vesting_schedule.get_challenge_reward_amounts_in_ocean"
        ) as mock:
            with sysargs_context(sys_args):
                mock.return_value = [30, 20]
                dftool_module.do_calc()

    # test result
    rewards_csv = csvs.volume_rewards_csv_filename(CSV_DIR)
    assert os.path.exists(rewards_csv)

    # get total reward amount
    rewards = csvs.load_volume_rewards_csv(CSV_DIR)
    total_reward = 0
    for _, addrs in rewards.items():
        for _, reward in addrs.items():
            total_reward += reward
    assert total_reward == 74950.0


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

    df_rewards = B.DFRewards.deploy({"from": accounts[0]})

    # main command
    CSV_DIR = str(tmp_path)
    DFREWARDS_ADDR = df_rewards.address
    OCEAN_ADDR = oceanutil.OCEAN_address()

    # pylint: disable=line-too-long
    cmd = f"./dftool dispense_active {CSV_DIR} {CHAINID} --DFREWARDS_ADDR={DFREWARDS_ADDR} --TOKEN_ADDR={OCEAN_ADDR}"
    os.system(cmd)

    # test result
    assert from_wei(df_rewards.claimable(address1, OCEAN_ADDR)) == 700.0
    assert from_wei(df_rewards.claimable(address2, OCEAN_ADDR)) == 100.0


@enforce_types
def test_manyrandom():
    cmd = f"./dftool manyrandom {CHAINID}"
    output_s = ""
    with subprocess.Popen(
        cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    ) as proc:
        while proc.poll() is None:
            output_s += proc.stdout.readline().decode("ascii")
    return_code = proc.wait()
    assert return_code == 0, f"Error. \n{output_s}"


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
    account9 = brownie.network.accounts[9]

    OCEAN = oceanutil.OCEANtoken()
    if OCEAN.balanceOf(account9.address) == 0.0:
        assert from_wei(OCEAN.balanceOf(account9.address)) == 0.0

        cmd = f"./dftool initdevwallets {networkutil.DEV_CHAINID}"
        os.system(cmd)

        assert from_wei(OCEAN.balanceOf(account9.address)) > 1.0


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
    with sysargs_context(sys_argv):
        with pytest.raises(SystemExit):
            dftool_module.do_volsym()

    rate_file = os.path.join(tmp_path, "rate-test.csv")
    Path(rate_file).write_text("")

    with sysargs_context(sys_argv):
        with patch.object(dftool_module, "retryFunction") as mock:
            mock.return_value = ({}, {}, {})
            dftool_module.do_volsym()

    assert os.path.exists(os.path.join(CSV_DIR, "nftvols-8996.csv"))
    assert os.path.exists(os.path.join(CSV_DIR, "owners-8996.csv"))
    assert os.path.exists(os.path.join(CSV_DIR, "symbols-8996.csv"))


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
