import datetime
import os
import subprocess
import sys
from unittest.mock import patch

import brownie
from df_py.predictoor.models import Prediction, Predictoor
from enforce_typing import enforce_types

from df_py.predictoor.csvs import (
    loadPredictoorData,
    loadPredictoorRewards,
    predictoorDataFilename,
    predictoorRewardsFilename,
    savePredictoorData,
)
from df_py.predictoor.predictoor_testutil import create_mock_responses
from df_py.util import networkutil, oceantestutil, oceanutil
from df_py.util.base18 import from_wei, to_wei
from df_py.util.constants import BROWNIE_PROJECT as B
from df_py.util.dftool_module import do_predictoor_data
from df_py.volume import csvs

PREV, DFTOOL_ACCT = {}, None

CHAINID = networkutil.DEV_CHAINID
ADDRESS_FILE = networkutil.chainIdToAddressFile(CHAINID)


@enforce_types
def test_calc(tmp_path):
    CSV_DIR = str(tmp_path)
    OCEAN_addr = oceanutil.OCEAN_address()

    # insert fake csvs
    allocations = {CHAINID: {"0xnft_addra": {"0xlp_addr1": 1.0}}}
    csvs.saveAllocationCsv(allocations, CSV_DIR)

    nftvols_at_chain = {OCEAN_addr: {"0xnft_addra": 1.0}}
    csvs.saveNftvolsCsv(nftvols_at_chain, CSV_DIR, CHAINID)

    owners_at_chain = {"0xnft_addra": "0xlp_addr1"}
    csvs.saveOwnersCsv(owners_at_chain, CSV_DIR, CHAINID)

    vebals = {"0xlp_addr1": 1.0}
    locked_amt = {"0xlp_addr1": 10.0}
    unlock_time = {"0xlp_addr1": 1}
    csvs.saveVebalsCsv(vebals, locked_amt, unlock_time, CSV_DIR)

    symbols_at_chain = {OCEAN_addr: "OCEAN"}
    csvs.saveSymbolsCsv(symbols_at_chain, CSV_DIR, CHAINID)

    csvs.saveRateCsv("OCEAN", 0.50, CSV_DIR)

    # main cmd
    TOT_OCEAN = 1000.0
    START_DATE = "2023-02-02"  # Only substream is volume DF
    SUBSTREAM_NAME = "volume"
    cmd = f"./dftool calc {CSV_DIR} {TOT_OCEAN} {START_DATE} {SUBSTREAM_NAME}"
    os.system(cmd)

    # test result
    rewards_csv = csvs.rewardsperlpCsvFilename(CSV_DIR, "OCEAN")
    assert os.path.exists(rewards_csv)


@enforce_types
def test_predictoor_data(tmp_path):
    CSV_DIR = str(tmp_path)
    ST = 0
    FIN = "latest"

    testargs = ["dftool", "predictoor_data", CSV_DIR, ST, FIN, CHAINID]
    mock_query_response, users, stats = create_mock_responses(100)

    with patch.object(sys, "argv", testargs):
        with patch("df_py.predictoor.queries.submitQuery") as mock_submitQuery:
            mock_submitQuery.side_effect = mock_query_response
            do_predictoor_data()

    # test result
    predictoor_data_csv = predictoorDataFilename(CSV_DIR, CHAINID)
    assert os.path.exists(predictoor_data_csv)

    predictoors = loadPredictoorData(CSV_DIR, CHAINID)
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
    for i in range(1, 5):  # chainids
        predictoor_data_csv = predictoorDataFilename(CSV_DIR, i)
        with open(predictoor_data_csv, "w") as f:
            f.write(csv_template)

    # main cmd
    SUBSTREAM = "predictoor"

    # TEST WITH TOT_OCEAN > 0
    TOT_OCEAN = 1000.0
    ST = "2023-03-16"  # first week of df main
    cmd = f"./dftool calc {CSV_DIR} {TOT_OCEAN} {ST} {SUBSTREAM}"
    os.system(cmd)

    # test result
    rewards_csv = predictoorRewardsFilename(CSV_DIR, "OCEAN")
    assert os.path.exists(rewards_csv)

    # get total reward amount
    rewards = loadPredictoorRewards(CSV_DIR, "OCEAN")
    total_reward = sum(rewards.values())
    assert total_reward == 1000.0

    # delete rewards csv
    os.remove(rewards_csv)

    # TEST WITH TOT_OCEAN = 0, DATE WITH NONZERO REWARDS
    TOT_OCEAN = 0
    ST = "2025-03-16"  # some date where predictoor rewards are nonzero
    cmd = f"./dftool calc {CSV_DIR} {TOT_OCEAN} {ST} {SUBSTREAM}"
    os.system(cmd)

    # test result
    rewards_csv = predictoorRewardsFilename(CSV_DIR, "OCEAN")
    assert os.path.exists(rewards_csv)
    rewards = loadPredictoorRewards(CSV_DIR, "OCEAN")
    total_reward = sum(rewards.values())
    assert total_reward > 0

    # delete rewards csv
    os.remove(rewards_csv)

    # TEST WITH TOT_OCEAN = 0, DATE WITH ZERO REWARDS
    TOT_OCEAN = 0
    ST = "2023-01-01"  # some date where predictoor rewards are zero
    cmd = f"./dftool calc {CSV_DIR} {TOT_OCEAN} {ST} {SUBSTREAM}"
    os.system(cmd)

    # test result
    rewards_csv = predictoorRewardsFilename(CSV_DIR, "OCEAN")
    assert os.path.exists(rewards_csv)
    rewards = loadPredictoorRewards(CSV_DIR, "OCEAN")
    total_reward = sum(rewards.values())
    assert total_reward == 0


@enforce_types
def test_calc_without_amount(tmp_path):
    CSV_DIR = str(tmp_path)
    OCEAN_addr = oceanutil.OCEAN_address()

    # insert fake csvs
    allocations = {CHAINID: {"0xnft_addra": {"0xlp_addr1": 1.0}}}
    csvs.saveAllocationCsv(allocations, CSV_DIR)

    nftvols_at_chain = {OCEAN_addr: {"0xnft_addra": 1e10}}
    csvs.saveNftvolsCsv(nftvols_at_chain, CSV_DIR, CHAINID)

    owners_at_chain = {"0xnft_addra": "0xlp_addr1"}
    csvs.saveOwnersCsv(owners_at_chain, CSV_DIR, CHAINID)

    vebals = {"0xlp_addr1": 1e8}
    locked_amt = {"0xlp_addr1": 10.0}
    unlock_time = {"0xlp_addr1": 1}
    csvs.saveVebalsCsv(vebals, locked_amt, unlock_time, CSV_DIR)

    symbols_at_chain = {OCEAN_addr: "OCEAN"}
    csvs.saveSymbolsCsv(symbols_at_chain, CSV_DIR, CHAINID)

    csvs.saveRateCsv("OCEAN", 0.50, CSV_DIR)

    # main cmd
    TOT_OCEAN = 0
    ST = "2023-03-16"  # first week of df main
    cmd = f"./dftool calc {CSV_DIR} {TOT_OCEAN} {ST}"
    os.system(cmd)

    # test result
    rewards_csv = csvs.rewardsperlpCsvFilename(CSV_DIR, "OCEAN")
    assert os.path.exists(rewards_csv)

    # get total reward amount
    rewards = csvs.loadRewardsCsv(CSV_DIR, "OCEAN")
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
    csvs.saveRewardsperlpCsv(rewards, CSV_DIR, "OCEAN")

    df_rewards = B.DFRewards.deploy({"from": accounts[0]})

    # main command
    CSV_DIR = str(tmp_path)
    DFREWARDS_ADDR = df_rewards.address
    OCEAN_ADDR = oceanutil.OCEAN_address()

    cmd = f"./dftool dispense_active {CSV_DIR} {CHAINID} {DFREWARDS_ADDR} {OCEAN_ADDR}"
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
    csvs.saveVebalsCsv(fake_vebals, locked_amt, unlock_times, CSV_DIR, False)
    date = chain.time() // S_PER_WEEK * S_PER_WEEK
    date = datetime.datetime.utcfromtimestamp(date).strftime("%Y-%m-%d")
    cmd = f"./dftool calculate_passive {CHAINID} {date} {CSV_DIR}"
    os.system(cmd)

    filename = csvs.passiveCsvFilename(CSV_DIR)
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
