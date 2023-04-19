import os
import subprocess
import datetime

import brownie
from enforce_typing import enforce_types

from util import csvs, networkutil, oceanutil, oceantestutil
from util.base18 import fromBase18, toBase18
from util.constants import BROWNIE_PROJECT as B

from util.oceanutil import (
    get_lock_end_veocean,
)

PREV, DFTOOL_ACCT = {}, None

CHAINID = networkutil.DEV_CHAINID
ADDRESS_FILE = networkutil.chainIdToAddressFile(CHAINID)


@enforce_types
def test_getrate(tmp_path):
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
    cmd = f"./dftool calc {CSV_DIR} {TOT_OCEAN}"
    os.system(cmd)

    # test result
    rewards_csv = csvs.rewardsperlpCsvFilename(CSV_DIR, "OCEAN")
    assert os.path.exists(rewards_csv)


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
    OCEAN.transfer(DFTOOL_ACCT, toBase18(TOT_OCEAN), {"from": accounts[0]})
    assert fromBase18(OCEAN.balanceOf(DFTOOL_ACCT.address)) == TOT_OCEAN

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
    assert fromBase18(df_rewards.claimable(address1, OCEAN_ADDR)) == 700.0
    assert fromBase18(df_rewards.claimable(address2, OCEAN_ADDR)) == 100.0


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
def test_initdevwallets():
    accounts = brownie.network.accounts

    OCEAN = oceanutil.OCEANtoken()
    curBal = fromBase18(OCEAN.balanceOf(accounts[9].address))
    assert curBal >= 1000.0

    # initdevwallets only fills wallets if < 1000.0
    balOut = curBal - 999.0
    OCEAN.transfer(accounts[0], toBase18(balOut), {"from": accounts[9]})
    cmd = f"./dftool initdevwallets {networkutil.DEV_CHAINID}"
    os.system(cmd)

    assert fromBase18(OCEAN.balanceOf(accounts[9].address)) == 1999.0


@enforce_types
def test_create_lock_amount_veocean():
    accounts = brownie.network.accounts

    OCEAN = oceanutil.OCEANtoken()
    veOCEAN = oceanutil.veOCEAN()
    
    # Let's set alice to be DF_TOOL
    global DFTOOL_ACCT
    alice = accounts.add()
    os.environ["DFTOOL_KEY"] = alice.private_key
    
    # Dispense funds to alice
    OCEAN = oceanutil.OCEANtoken()
    OCEAN.transfer(alice.address, toBase18(100.0), {"from": accounts[0]})
    assert fromBase18(OCEAN.balanceOf(alice.address)) == 100.0
    
    # Create lock for alice
    assert veOCEAN.balanceOf(alice.address) == 0
    cmd = f"./dftool create_lock_veocean {networkutil.DEV_CHAINID} 100 10"
    os.system(cmd)

    # Assert alice has no more OCEAN
    assert OCEAN.balanceOf(alice) == 0.0

    # reset DFTOOL_KEY to DFTOOL_ACCT
    os.environ["DFTOOL_KEY"] = DFTOOL_ACCT.private_key


@enforce_types
def test_increase_lock_amount_veocean():
    accounts = brownie.network.accounts
    
    OCEAN = oceanutil.OCEANtoken()
    veOCEAN = oceanutil.veOCEAN()
    S_PER_WEEK = 604800

    # Let's set alice to be DF_TOOL
    global DFTOOL_ACCT
    alice = accounts.add()
    os.environ["DFTOOL_KEY"] = alice.private_key
    
    # Dispense funds to alice
    OCEAN = oceanutil.OCEANtoken()
    OCEAN.transfer(alice.address, toBase18(200.0), {"from": accounts[0]})
    assert fromBase18(OCEAN.balanceOf(alice.address)) == 200.0
    
    # Create lock for alice
    assert veOCEAN.balanceOf(alice.address) == 0
    cmd = f"./dftool create_lock_veocean {networkutil.DEV_CHAINID} 100 10"
    os.system(cmd)

    # Assert alice has 100 OCEAN left
    assert fromBase18(OCEAN.balanceOf(alice)) == 100.0

    cmd = f"./dftool increase_lock_amount_veocean {networkutil.DEV_CHAINID} 100"
    os.system(cmd)

    # Assert alice has 0 OCEAN left
    assert OCEAN.balanceOf(alice) == 0.0

    # reset DFTOOL_KEY to DFTOOL_ACCT
    os.environ["DFTOOL_KEY"] = DFTOOL_ACCT.private_key


@enforce_types
def test_increase_unlock_time_veocean():
    
    OCEAN = oceanutil.OCEANtoken()
    veOCEAN = oceanutil.veOCEAN()
    S_PER_WEEK = 604800

    # if lock expired, withdraw
    cur_lock_end = get_lock_end_veocean(account0.address)
    print("cur_lock_end", cur_lock_end)
    print("brownie.network.chain.time()", brownie.network.chain.time())
    if brownie.network.chain.time() > cur_lock_end :
        veOCEAN.withdraw({"from": account0})
        
    ve_ocean_balance = veOCEAN.balanceOf(account0.address)
    print("ve_ocean_balance", ve_ocean_balance)
    # If no balance, create lock
    if veOCEAN.balanceOf(account0.address) == 0.0 :
        veOCEAN.withdraw({"from": lock_account})

        OCEAN_lock_amt = toBase18(5.0)
        OCEAN.approve(veOCEAN.address, OCEAN_lock_amt, {"from": account0})
        
        # Lock veOCEAN
        t0 = brownie.network.chain.time()
        t1 = t0 // S_PER_WEEK * S_PER_WEEK + S_PER_WEEK
        brownie.network.chain.sleep(t1 - t0)
        t2 = brownie.network.chain.time() + S_PER_WEEK * 20  # lock for 20 weeks
        veOCEAN.create_lock(OCEAN_lock_amt, t2, {"from": account0})

    first_lock_end = get_lock_end_veocean(account0.address)
    cur_time = brownie.network.chain.time()
        
    if first_lock_end > cur_time :    
        print("first_lock_end", first_lock_end)
        assert first_lock_end > 0

        cmd = f"./dftool increase_unlock_time_veocean {networkutil.DEV_CHAINID} 10"
        os.system(cmd)

        # Verify the lock end time has changed
        second_lock_end = get_lock_end_veocean(account0.address)
        print("second_lock_end", second_lock_end)
        assert second_lock_end >= first_lock_end
    else :
        assert first_lock_end <= cur_time


@enforce_types
def test_withdraw_lock_amount_veocean():
    account0 = brownie.network.accounts[0]

    OCEAN = oceanutil.OCEANtoken()
    veOCEAN = oceanutil.veOCEAN()
    S_PER_WEEK = 604800

    lock_expiry: int256 = convert(VotingEscrow(VOTING_ESCROW).locked__end(_delegator), int256)
    cur_time = brownie.network.chain.time()
    
    if cur_time < t0 :
        first_balance = veOCEAN.balanceOf(account0.address)
        assert fromBase18(first_balance) > 0.0
        cmd = f"./dftool do_withdraw_ocean_from_lock {networkutil.DEV_CHAINID}"
        os.system(cmd)
        
        balanceOf = veOCEAN.balanceOf(account0.address)
        print("balanceOf", balanceOf)

        assert fromBase18(balanceOf) >= 0.0
    else :
        assert cur_time >= t0


@enforce_types
def test_noarg_commands():
    # Test commands that have no args. They're usually help commands;
    # sometimes they do the main work (eg compile).
    argv1s = [
        "",
        "volsym",
        "getrate",
        "calc",
        "dispense_active",
        "querymany",
        "compile",
        "manyrandom",
        "newdfrewards",
        "mine",
        "newacct",
        "newtoken",
        "acctinfo",
        "chaininfo",
        "get_balance_veocean",
        "get_lock_end_veocean",
        "new_veallocate",
    ]
    for argv1 in argv1s:
        print(f"Test dftool {argv1}")
        cmd = f"./dftool {argv1}"

        output_s = ""
        with subprocess.Popen(
            cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        ) as proc:
            while proc.poll() is None:
                output_s += proc.stdout.readline().decode("ascii")

        return_code = proc.wait()
        # bad commands - such as querymany - will still return 0 and do not fail
        assert return_code == 0, f"'dftool {argv1}' failed. \n{output_s}"


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
    OCEAN_lock_amt = toBase18(10.0)
    S_PER_WEEK = 604800
    chain = brownie.network.chain
    feeDistributor = oceanutil.FeeDistributor()
    veOCEAN = oceanutil.veOCEAN()
    CSV_DIR = str(tmp_path)
    unlock_time = chain.time() + S_PER_WEEK * 10

    for _ in range(2):
        acc = brownie.network.accounts.add()
        account0.transfer(acc, toBase18(0.1))
        OCEAN.transfer(acc, OCEAN_lock_amt, {"from": account0})
        # create lock
        OCEAN.approve(veOCEAN, OCEAN_lock_amt, {"from": acc})
        veOCEAN.create_lock(OCEAN_lock_amt, unlock_time, {"from": acc})
        accounts.append(acc)

    for _ in range(3):
        OCEAN.transfer(
            feeDistributor.address,
            toBase18(1000.0),
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
        fake_vebals[acc.address] = fromBase18(veOCEAN.balanceOf(acc.address))
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


@enforce_types
def setup_function():
    global PREV, DFTOOL_ACCT

    networkutil.connect(CHAINID)
    accounts = brownie.network.accounts
    oceanutil.recordDevDeployedContracts()
    oceantestutil.fillAccountsWithOCEAN()

    DFTOOL_ACCT = accounts.add()
    accounts[0].transfer(DFTOOL_ACCT, toBase18(0.001))

    for envvar in ["DFTOOL_KEY", "ADDRESS_FILE", "SUBGRAPH_URI", "SECRET_SEED"]:
        PREV[envvar] = os.environ.get(envvar)

    os.environ["DFTOOL_KEY"] = DFTOOL_ACCT.private_key
    os.environ["ADDRESS_FILE"] = ADDRESS_FILE
    os.environ["SUBGRAPH_URI"] = networkutil.chainIdToSubgraphUri(CHAINID)
    os.environ["SECRET_SEED"] = "1234"


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
