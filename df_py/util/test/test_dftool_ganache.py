import contextlib
import datetime
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from enforce_typing import enforce_types

from df_py.challenge.csvs import (
    challenge_data_csv_filename,
    load_challenge_rewards_csv,
    save_challenge_rewards_csv,
)
from df_py.predictoor.csvs import (
    load_predictoor_data_csv,
    load_predictoor_rewards_csv,
    predictoor_data_csv_filename,
    predictoor_rewards_csv_filename,
    sample_predictoor_data_csv,
)
from df_py.predictoor.models import PredictContract
from df_py.predictoor.predictoor_testutil import create_mock_responses
from df_py.util import dftool_module, networkutil, oceantestutil, oceanutil
from df_py.util.base18 import from_wei, to_wei
from df_py.util.contract_base import ContractBase
from df_py.util.dftool_module import do_predictoor_data
from df_py.util.get_rate import get_rate
from df_py.volume import csvs

PREV, DFTOOL_ACCT = {}, None

CHAINID = networkutil.DEV_CHAINID
ADDRESS_FILE = networkutil.chain_id_to_address_file(CHAINID)


@contextlib.contextmanager
def sysargs_context(arguments):
    old_sys_argv = sys.argv
    sys.argv = arguments
    yield
    sys.argv = old_sys_argv


@pytest.fixture
def mock_query_predictoor_contracts():
    with patch("df_py.predictoor.calc_rewards.query_predictoor_contracts") as mock:
        mock.return_value = {
            "0xContract1": PredictContract(8996, "0x1", "c1", "c1", 10, 20),
            "0xContract2": PredictContract(8996, "0x2", "c2", "c2", 10, 20),
        }
        yield mock


@enforce_types
def test_calc_volume(tmp_path):
    csv_dir = str(tmp_path)
    OCEAN_addr = oceanutil.OCEAN_address(networkutil.DEV_CHAINID)

    # insert fake csvs
    allocations = {CHAINID: {"0xnft_addra": {"0xlp_addr1": 1.0}}}
    csvs.save_allocation_csv(allocations, csv_dir)

    nftvols_at_chain = {OCEAN_addr: {"0xnft_addra": 1.0}}
    csvs.save_nftvols_csv(nftvols_at_chain, csv_dir, CHAINID)

    owners_at_chain = {"0xnft_addra": "0xlp_addr1"}
    csvs.save_owners_csv(owners_at_chain, csv_dir, CHAINID)

    vebals = {"0xlp_addr1": 1.0}
    locked_amt = {"0xlp_addr1": 10.0}
    unlock_time = {"0xlp_addr1": 1}
    csvs.save_vebals_csv(vebals, locked_amt, unlock_time, csv_dir)

    symbols_at_chain = {OCEAN_addr: "OCEAN"}
    csvs.save_symbols_csv(symbols_at_chain, csv_dir, CHAINID)

    csvs.save_rate_csv("OCEAN", 0.50, csv_dir)

    # main cmd
    TOT_OCEAN = 1000.0
    START_DATE = "2023-02-02"  # Only substream is volume DF

    with patch("web3.main.Web3.to_checksum_address") as mock:
        mock.side_effect = lambda value: value
        with sysargs_context(
            [
                "dftool",
                "calc",
                "volume",
                csv_dir,
                str(TOT_OCEAN),
                f"--START_DATE={START_DATE}",
            ]
        ):
            dftool_module.do_calc()

    # test result
    rewards_csv = csvs.volume_rewards_csv_filename(csv_dir)
    assert os.path.exists(rewards_csv)


# pylint: disable=redefined-outer-name
@enforce_types
def test_calc_failures(tmp_path):
    csv_dir = str(tmp_path)

    # neither total ocean, nor given start date
    with pytest.raises(SystemExit):
        with sysargs_context(["dftool", "calc", "volume", csv_dir, "0"]):
            dftool_module.do_calc()

    tot_ocean = 1000.0
    start_date = "2023-02-02"  # Only substream is volume DF

    # no required input files -- volume
    with pytest.raises(SystemExit):
        with sysargs_context(
            [
                "dftool",
                "calc",
                "volume",
                csv_dir,
                str(tot_ocean),
                f"--START_DATE={start_date}",
            ]
        ):
            dftool_module.do_calc()

    # no required input files -- challenge
    with pytest.raises(SystemExit):
        with sysargs_context(
            [
                "dftool",
                "calc",
                "challenge",
                csv_dir,
                str(tot_ocean),
                f"--START_DATE={start_date}",
                f"--CHAINID={networkutil.DEV_CHAINID}",
            ]
        ):
            dftool_module.do_calc()


@enforce_types
def test_predictoor_data(tmp_path):
    with patch("df_py.util.dftool_module.query_predictoor_contracts") as mock:
        mock.return_value = {
            "0xContract1": PredictContract(8996, "0x1", "c1", "c1", 10, 20),
            "0xContract2": PredictContract(8996, "0x2", "c2", "c2", 10, 20),
        }

        csv_dir = str(tmp_path)

        sys_argv = [
            "dftool",
            "predictoor_data",
            "2023-10-01",
            "2023-10-07",
            csv_dir,
            str(CHAINID),
            "--RETRIES=1",
        ]

        mock_query_response, users, stats = create_mock_responses(100)

        with sysargs_context(sys_argv):
            with patch("df_py.predictoor.queries.submit_query") as mock_submit_query:
                mock_submit_query.side_effect = mock_query_response
                do_predictoor_data()

        # test result
        predictoor_data_csv = predictoor_data_csv_filename(csv_dir)
        assert os.path.exists(predictoor_data_csv)

        predictoors = load_predictoor_data_csv(csv_dir)
        for user in users:
            if stats[user]["total"] == 0:
                assert user not in predictoors
                continue
            user_total = stats[user]["total"]
            user_correct = stats[user]["correct"]
            user_revenue = stats[user]["revenue"]
            assert predictoors[user].prediction_count == user_total
            assert predictoors[user].correct_prediction_count == user_correct
            assert predictoors[user].revenue == user_revenue
            assert predictoors[user].accuracy == user_correct / user_total


def test_dummy_csvs(tmp_path):
    csv_dir = str(tmp_path)
    with sysargs_context(
        [
            "dftool",
            "dummy_csvs",
            "challenge",
            csv_dir,
        ]
    ):
        dftool_module.do_dummy_csvs()

    challenge_data_csv = challenge_data_csv_filename(csv_dir)
    challenge_rewards_csv = predictoor_rewards_csv_filename(csv_dir)
    assert challenge_data_csv
    assert challenge_rewards_csv


@patch(
    "df_py.challenge.calc_rewards.CHALLENGE_FIRST_DATE", datetime.datetime(2021, 1, 1)
)
@enforce_types
def test_calc_challenge_substream(tmp_path):
    csv_dir = str(tmp_path)

    csv_template = """from_addr,nft_addr,nmse
0x0000000000000000000000000000000000000001,0x01,0.1
0x1000000000000000000000000000000000000001,0x02,0.122
0x2000000000000000000000000000000000000001,0x03,0.3
0x3000000000000000000000000000000000000001,0x04,0.8
0x4000000000000000000000000000000000000001,0x05,0.88
"""
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    safe_limit = 1300 * (1 / get_rate("OCEAN", today, today))

    challenge_data_csv = challenge_data_csv_filename(csv_dir)
    with open(challenge_data_csv, "w") as f:
        f.write(csv_template)

    csv_dir = str(tmp_path)

    with sysargs_context(["dftool", "calc", "challenge", csv_dir, str(safe_limit)]):
        dftool_module.do_calc()

    rewards = load_challenge_rewards_csv(csv_dir)
    assert len(rewards) == 3
    assert rewards["0x0000000000000000000000000000000000000001"] > 0

    # not enough available tokens
    with sysargs_context(["dftool", "calc", "challenge", csv_dir, "750"]):
        with pytest.raises(SystemExit):
            dftool_module.do_calc()

    # no rewards case:
    csv_template = "from_addr,nft_addr,nmse"

    with open(challenge_data_csv, "w") as f:
        f.write(csv_template)

    with sysargs_context(["dftool", "calc", "challenge", csv_dir, str(safe_limit)]):
        with pytest.raises(SystemExit):
            dftool_module.do_calc()


@enforce_types
@patch("df_py.predictoor.calc_rewards.query_predictoor_contracts")
def test_calc_predictoor_rose_substream(mock_query_predictoor_contracts, tmp_path):
    csv_dir = str(tmp_path)

    predictoor_data_csv = predictoor_data_csv_filename(csv_dir)
    sample_data = sample_predictoor_data_csv(50000)
    contract_addresses = {f"0xContract{i}": 0 for i in range(1, 4)}
    mock_query_predictoor_contracts.return_value = contract_addresses
    with open(predictoor_data_csv, "w") as f:
        f.write(sample_data)

    csv_dir = str(tmp_path)

    with sysargs_context(["dftool", "calc", "predictoor_rose", csv_dir, "100000"]):
        dftool_module.do_calc()

    rewards = load_predictoor_rewards_csv(csv_dir)
    print(rewards)
    assert len(rewards) == 3
    for address in contract_addresses:
        assert len(rewards[address.lower()]) > 1000


@enforce_types
def test_calc_without_amount(tmp_path, monkeypatch):
    monkeypatch.setenv("GOERLI_RPC_URL", "http://localhost:8545")
    csv_dir = str(tmp_path)
    OCEAN_addr = oceanutil.OCEAN_address(networkutil.DEV_CHAINID)

    # insert fake csvs
    allocations = {CHAINID: {"0xnft_addra": {"0xlp_addr1": 1.0}}}
    csvs.save_allocation_csv(allocations, csv_dir)

    nftvols_at_chain = {OCEAN_addr: {"0xnft_addra": 1e10}}
    csvs.save_nftvols_csv(nftvols_at_chain, csv_dir, CHAINID)

    owners_at_chain = {"0xnft_addra": "0xlp_addr1"}
    csvs.save_owners_csv(owners_at_chain, csv_dir, CHAINID)

    vebals = {"0xlp_addr1": 1e8}
    locked_amt = {"0xlp_addr1": 10.0}
    unlock_time = {"0xlp_addr1": 1}
    csvs.save_vebals_csv(vebals, locked_amt, unlock_time, csv_dir)

    symbols_at_chain = {OCEAN_addr: "OCEAN"}
    csvs.save_symbols_csv(symbols_at_chain, csv_dir, CHAINID)

    csvs.save_rate_csv("OCEAN", 0.50, csv_dir)

    # main cmd
    start_date = "2023-03-16"  # first week of df main
    sys_args = ["dftool", "calc", "volume", csv_dir, "0", f"--START_DATE={start_date}"]

    with patch("web3.main.Web3.to_checksum_address") as mock_checksum:
        mock_checksum.side_effect = lambda value: value
        with patch("df_py.util.dftool_module.record_deployed_contracts") as mock:
            with patch(
                "df_py.util.vesting_schedule.get_challenge_reward_amounts_in_ocean"
            ) as mock:
                with sysargs_context(sys_args):
                    mock.return_value = [30, 20]
                    dftool_module.do_calc()

    # test result
    rewards_csv = csvs.volume_rewards_csv_filename(csv_dir)
    assert os.path.exists(rewards_csv)

    # get total reward amount
    with patch("web3.main.Web3.to_checksum_address") as mock_checksum:
        mock_checksum.side_effect = lambda value: value
        rewards = csvs.load_volume_rewards_csv(csv_dir)

    total_reward = 0
    for _, addrs in rewards.items():
        for _, reward in addrs.items():
            total_reward += reward
    assert total_reward == 74950.0


@enforce_types
def test_dispense(tmp_path, all_accounts, account0, w3):
    # values used for inputs or main cmd
    address1 = all_accounts[1].address
    address2 = all_accounts[2].address
    csv_dir = str(tmp_path)
    tot_ocean = 4000.0

    # accounts[0] has OCEAN. Ensure that ispensing account has some
    global DFTOOL_ACCT
    OCEAN = oceanutil.OCEAN_token(networkutil.DEV_CHAINID)
    OCEAN.transfer(DFTOOL_ACCT, to_wei(tot_ocean), {"from": account0})
    assert from_wei(OCEAN.balanceOf(DFTOOL_ACCT.address)) == tot_ocean

    # insert fake inputs: rewards csv, new dfrewards.sol contract
    rewards = {
        CHAINID: {address1: 400},
        "5": {address1: 300, address2: 100},
    }
    csvs.save_volume_rewards_csv(rewards, csv_dir)
    challenge_rewards = [
        {"winner_addr": address1, "OCEAN_amt": 2000},
        {"winner_addr": address2, "OCEAN_amt": 1000},
    ]
    save_challenge_rewards_csv(challenge_rewards, csv_dir)
    df_rewards = ContractBase(w3, "DFRewards", constructor_args=[])

    # main command
    csv_dir = str(tmp_path)
    DFRewards_addr = df_rewards.address
    OCEAN_addr = w3.to_checksum_address(oceanutil.OCEAN_address(CHAINID))

    sys_argv = [
        "dftool",
        "dispense_active",
        csv_dir,
        str(CHAINID),
        f"--DFREWARDS_ADDR={DFRewards_addr}",
        f"--TOKEN_ADDR={OCEAN_addr}",
    ]

    with sysargs_context(sys_argv):
        dftool_module.do_dispense_active()

    # test result
    assert from_wei(df_rewards.claimable(address1, OCEAN_addr)) == 2700.0
    assert from_wei(df_rewards.claimable(address2, OCEAN_addr)) == 1100.0


# TODO: re-enable. pylint: disable=fixme
@pytest.mark.skip("test_all from queries only works with this disabled.")
@enforce_types
def test_many_random():
    sys_argv = [
        "dftool",
        "many_random",
        str(CHAINID),
    ]

    with sysargs_context(sys_argv):
        dftool_module.do_many_random()

    # different chain id will fail
    sys_argv = ["dftool", "many_random", "3"]

    with pytest.raises(SystemExit):
        with sysargs_context(sys_argv):
            dftool_module.do_many_random()


@enforce_types
def test_checkpoint_feedistributor(w3):
    fee_distributor = oceanutil.FeeDistributor(CHAINID)
    timecursor_before = fee_distributor.time_cursor()
    provider = w3.provider
    provider.make_request("evm_mine", [])
    provider.make_request("evm_increaseTime", [60 * 60 * 24 * 7])
    cmd = f"./dftool checkpoint_feedist {CHAINID}"
    os.system(cmd)

    timecursor_after = fee_distributor.time_cursor()

    assert timecursor_after > timecursor_before


@enforce_types
def test_calc_passive(tmp_path, account0, w3):
    accounts = []
    OCEAN = oceanutil.OCEAN_token(networkutil.DEV_CHAINID)
    OCEAN_lock_amt = to_wei(10.0)
    S_PER_WEEK = 604800

    feeDistributor = oceanutil.FeeDistributor(networkutil.DEV_CHAINID)
    veOCEAN = oceanutil.veOCEAN(networkutil.DEV_CHAINID)
    csv_dir = str(tmp_path)
    unlock_time = w3.eth.get_block("latest").timestamp + S_PER_WEEK * 10
    provider = w3.provider

    sys_argv = [
        "dftool",
        "calculate_passive",
        str(networkutil.DEV_CHAINID),
        "2023-02-02",
        csv_dir,
    ]

    # fails without vebals file
    with patch.object(dftool_module, "record_deployed_contracts"):
        with pytest.raises(SystemExit):
            with sysargs_context(sys_argv):
                dftool_module.do_calculate_passive()

    for _ in range(2):
        acc = w3.eth.account.create()
        networkutil.send_ether(w3, account0, acc.address, OCEAN_lock_amt)
        OCEAN.transfer(acc, OCEAN_lock_amt, {"from": account0})
        # create lock
        OCEAN.approve(veOCEAN, OCEAN_lock_amt, {"from": acc})
        veOCEAN.create_lock(OCEAN_lock_amt, unlock_time, {"from": acc})
        accounts.append(acc)

    for _ in range(3):
        OCEAN.transfer(
            feeDistributor.address,
            to_wei(1000.0),
            {"from": account0},
        )
        provider.make_request("evm_increaseTime", [S_PER_WEEK])
        provider.make_request("evm_mine", [])

        feeDistributor.checkpoint_token({"from": account0})
        feeDistributor.checkpoint_total_supply({"from": account0})

    fake_vebals = {}
    locked_amt = {}
    unlock_times = {}

    for acc in accounts:
        fake_vebals[acc.address] = from_wei(veOCEAN.balanceOf(acc.address))
        locked_amt[acc.address] = OCEAN_lock_amt
        unlock_times[acc.address] = unlock_time

    csvs.save_vebals_csv(fake_vebals, locked_amt, unlock_times, csv_dir, False)
    date = w3.eth.get_block("latest").timestamp // S_PER_WEEK * S_PER_WEEK
    date = datetime.datetime.utcfromtimestamp(date).strftime("%Y-%m-%d")

    sys_argv = ["dftool", "calculate_passive", str(CHAINID), str(date), csv_dir]

    with patch.object(dftool_module, "record_deployed_contracts"):
        with sysargs_context(sys_argv):
            dftool_module.do_calculate_passive()

    filename = csvs.passive_csv_filename(csv_dir)
    assert os.path.exists(filename)

    # number of lines must be >=3
    with open(filename, "r") as f:
        lines = f.readlines()
        assert len(lines) >= 3


def test_init_dev_wallets(all_accounts):
    account8 = all_accounts[7]
    account9 = all_accounts[8]

    OCEAN = oceanutil.OCEAN_token(networkutil.DEV_CHAINID)
    OCEAN.transfer(account8, OCEAN.balanceOf(account9.address), {"from": account9})

    assert from_wei(OCEAN.balanceOf(account9.address)) == 0.0

    sys_argv = ["dftool", "init_dev_wallets", str(networkutil.DEV_CHAINID)]

    with sysargs_context(sys_argv):
        dftool_module.do_init_dev_wallets()

    assert from_wei(OCEAN.balanceOf(account9.address)) > 1.0

    # different chain id will fail
    sys_argv = ["dftool", "init_dev_wallets", "3"]

    with pytest.raises(SystemExit):
        with sysargs_context(sys_argv):
            dftool_module.do_init_dev_wallets()


def test_volsym(tmp_path):
    csv_dir = str(tmp_path)

    sys_argv = [
        "dftool",
        "volsym",
        "2023-03-16",  # first week of df main
        "latest",
        "10",
        csv_dir,
        str(networkutil.DEV_CHAINID),
    ]

    # rates does not exist

    with sysargs_context(sys_argv):
        with pytest.raises(SystemExit):
            dftool_module.do_volsym()

    rate_file = os.path.join(tmp_path, "rate-test.csv")
    Path(rate_file).write_text("")

    with patch.object(dftool_module, "retry_function") as mock:
        with sysargs_context(sys_argv):
            mock.return_value = ({}, {}, {})
            dftool_module.do_volsym()

    assert os.path.exists(os.path.join(csv_dir, "nftvols-8996.csv"))
    assert os.path.exists(os.path.join(csv_dir, "owners-8996.csv"))
    assert os.path.exists(os.path.join(csv_dir, "symbols-8996.csv"))

    os.remove(os.path.join(csv_dir, "nftvols-8996.csv"))
    os.remove(os.path.join(csv_dir, "owners-8996.csv"))
    os.remove(os.path.join(csv_dir, "symbols-8996.csv"))

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
    csv_dir = str(tmp_path)

    sys_argv = [
        "dftool",
        "nftinfo",
        csv_dir,
        str(networkutil.DEV_CHAINID),
    ]

    with sysargs_context(sys_argv):
        with patch.object(dftool_module, "retry_function") as mock:
            mock.return_value = []
            dftool_module.do_nftinfo()

    assert os.path.exists(os.path.join(csv_dir, "nftinfo_8996.csv"))


def test_allocations(tmp_path):
    csv_dir = str(tmp_path)

    sys_argv = [
        "dftool",
        "allocations",
        "0",
        "latest",
        "10",
        csv_dir,
        str(networkutil.DEV_CHAINID),
    ]

    with sysargs_context(sys_argv):
        with patch.object(dftool_module, "retry_function") as mock:
            mock.return_value = {}
            dftool_module.do_allocations()

    assert os.path.exists(os.path.join(csv_dir, "allocations.csv"))

    # file already exists
    with pytest.raises(SystemExit):
        with sysargs_context(sys_argv):
            dftool_module.do_allocations()


def test_vebals(tmp_path):
    csv_dir = str(tmp_path)

    sys_argv = [
        "dftool",
        "vebals",
        "0",
        "latest",
        "10",
        csv_dir,
        str(networkutil.DEV_CHAINID),
    ]

    with sysargs_context(sys_argv):
        with patch.object(dftool_module, "retry_function") as mock:
            mock.return_value = ({}, {}, {})
            dftool_module.do_vebals()

    assert os.path.exists(os.path.join(csv_dir, "vebals.csv"))


def test_df_strategies(monkeypatch, w3):
    monkeypatch.setenv("DFTOOL_KEY", os.getenv("TEST_PRIVATE_KEY0"))
    sys_argv = [
        "dftool",
        "new_df_rewards",
        str(networkutil.DEV_CHAINID),
    ]

    with sysargs_context(sys_argv):
        dftool_module.do_new_df_rewards()

    df_rewards = ContractBase(w3, "DFRewards", constructor_args=[])
    df_strategy = ContractBase(
        w3, "DFStrategyV1", constructor_args=[df_rewards.address]
    )

    sys_argv = [
        "dftool",
        "new_df_strategy",
        str(networkutil.DEV_CHAINID),
        df_rewards.address,
        "DFStrategyV1",
    ]

    with sysargs_context(sys_argv):
        dftool_module.do_new_df_strategy()

    sys_argv = [
        "dftool",
        "addstrategy",
        str(networkutil.DEV_CHAINID),
        df_rewards.address,
        df_strategy.address,
    ]

    with sysargs_context(sys_argv):
        dftool_module.do_add_strategy()

    sys_argv = [
        "dftool",
        "retire_strategy",
        str(networkutil.DEV_CHAINID),
        df_rewards.address,
        df_strategy.address,
    ]

    with sysargs_context(sys_argv):
        dftool_module.do_retire_strategy()


def test_get_rate(tmp_path):
    csv_dir = str(tmp_path)

    sys_argv = [
        "dftool",
        "get_rate",
        "OCEAN",
        "0",
        "latest",
        csv_dir,
    ]

    with sysargs_context(sys_argv):
        with patch.object(dftool_module, "retry_function") as mock:
            mock.return_value = 100.0
            dftool_module.do_get_rate()

    assert os.path.exists(os.path.join(csv_dir, "rate-OCEAN.csv"))


def test_mine():
    sys_argv = ["dftool", "mine", "10"]

    with sysargs_context(sys_argv):
        dftool_module.do_mine()

    sys_argv = ["dftool", "mine", "10"]

    with sysargs_context(sys_argv):
        dftool_module.do_mine()


def test_new_functions(monkeypatch):
    monkeypatch.setenv("DFTOOL_KEY", os.getenv("TEST_PRIVATE_KEY0"))
    sys_argv = ["dftool", "new_acct", str(networkutil.DEV_CHAINID)]

    with sysargs_context(sys_argv):
        dftool_module.do_new_acct()

    sys_argv = ["dftool", "new_token", str(networkutil.DEV_CHAINID)]

    with sysargs_context(sys_argv):
        dftool_module.do_new_token()

    sys_argv = ["dftool", "new_ve_allocate", str(networkutil.DEV_CHAINID)]

    with sysargs_context(sys_argv):
        dftool_module.do_new_veallocate()


def test_ve_set_allocation():
    OCEAN_addr = oceanutil.OCEAN_address(networkutil.DEV_CHAINID)
    sys_argv = [
        "dftool",
        "ve_set_allocation",
        str(networkutil.DEV_CHAINID),
        "10",
        OCEAN_addr,
    ]

    with sysargs_context(sys_argv):
        dftool_module.do_ve_set_allocation()


def test_acct_info():
    sys_argv = ["dftool", "acct_info", str(networkutil.DEV_CHAINID), "1"]

    with sysargs_context(sys_argv):
        dftool_module.do_acct_info()

    OCEAN_addr = oceanutil.OCEAN_address(networkutil.DEV_CHAINID)
    sys_argv = [
        "dftool",
        "acct_info",
        str(networkutil.DEV_CHAINID),
        "1",
        f"--TOKEN_ADDR={OCEAN_addr}",
    ]

    with sysargs_context(sys_argv):
        dftool_module.do_acct_info()


def test_chain_info():
    sys_argv = ["dftool", "chain_info", str(networkutil.DEV_CHAINID)]

    with sysargs_context(sys_argv):
        dftool_module.do_chain_info()


def test_dispense_passive():
    sys_argv = [
        "dftool",
        "dispense_passive",
        str(networkutil.DEV_CHAINID),
        "0",
        "2023-02-02",
    ]

    with patch.object(dftool_module, "retry_function"):
        with sysargs_context(sys_argv):
            dftool_module.do_dispense_passive()


@enforce_types
def setup_function():
    global DFTOOL_ACCT
    accounts = oceantestutil.get_all_accounts()
    oceanutil.record_dev_deployed_contracts()
    oceantestutil.fill_accounts_with_OCEAN(accounts)

    w3 = networkutil.chain_id_to_web3(8996)
    DFTOOL_ACCT = w3.eth.account.create()

    networkutil.send_ether(w3, accounts[0], DFTOOL_ACCT.address, to_wei(0.001))

    for envvar in [
        "DFTOOL_KEY",
        "ADDRESS_FILE",
        "SUBGRAPH_URI",
        "SECRET_SEED",
        "WEB3_INFURA_PROJECT_ID",
    ]:
        PREV[envvar] = os.environ.get(envvar)

    os.environ["DFTOOL_KEY"] = DFTOOL_ACCT._private_key.hex()
    os.environ["ADDRESS_FILE"] = ADDRESS_FILE
    os.environ["SUBGRAPH_URI"] = networkutil.chain_id_to_subgraph_uri(CHAINID)
    os.environ["SECRET_SEED"] = "1234"
    os.environ["WEB3_INFURA_PROJECT_ID"] = ""
