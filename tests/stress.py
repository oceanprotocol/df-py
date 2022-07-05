#  type: ignore
# pylint: skip-file

#######################################
# this part is required to access "util"
import os
import random
import sys
import inspect

# to prevent brownie from printing in loops
class HiddenPrints:
    def __enter__(self):
        self._original_stdout = sys.stdout
        sys.stdout = open(os.devnull, "w")

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout.close()
        sys.stdout = self._original_stdout


currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
#######################################

# %%
## Actual code starts here
import brownie
import time
from util import oceanutil, oceantestutil, networkutil
from util.constants import BROWNIE_PROJECT as B
from util.query import getApprovedTokens
from tqdm import tqdm
import json


CHAINID = networkutil.DEV_CHAINID
ADDRESS_FILE = networkutil.chainIdToAddressFile(networkutil.DEV_CHAINID)
NUMBER_OF_ACCOUNTS = 1000


def main():
    networkutil.connect(CHAINID)  # Connect to ganache
    oceanutil.recordDevDeployedContracts()  # Record deployed contract addresses on ganache

    CSV_DIR = str("/tmp/df_stress_test")

    NSAMP = 50
    test_accounts = []

    # store 10k private keys
    print("Collecting private keys...")
    pk_list = open("./tests/samples/pks.txt", "r")
    for pk in tqdm(random.sample(pk_list.read().split("\n"), NUMBER_OF_ACCOUNTS)):
        # acc = w3.eth.account.privateKeyToAccount(pk)
        # private_keys.append(acc)
        with HiddenPrints():
            test_accounts.append(brownie.network.accounts.add(pk))

    accounts = brownie.network.accounts
    assert len(test_accounts) == NUMBER_OF_ACCOUNTS

    OCEAN = oceanutil.OCEANtoken()

    ## Deploy pool
    print("Deploying pool")
    (DT, pool) = oceantestutil.deployPool(1000.0, 1.0, accounts[0], OCEAN)

    ## Fund all addresses
    total_balance = OCEAN.balanceOf(accounts[0])
    STAKE_AMT = 10.0
    DT_buy_amt = 1.0
    DT_buy_times = 1
    funding_for_each_addr = (STAKE_AMT + DT_buy_amt * DT_buy_times + 50) * 1e18

    assert total_balance > funding_for_each_addr

    print(
        "Funding accounts",
    )
    for acc in tqdm(test_accounts):
        with HiddenPrints():
            OCEAN.transfer(acc.address, funding_for_each_addr, {"from": accounts[0]})

    print("Adding stake")
    for acc in tqdm(test_accounts):
        with HiddenPrints():
            oceantestutil.addStake(pool, STAKE_AMT, acc, OCEAN)

    ST = len(brownie.network.chain)

    print("Buying and consuming DT")
    for acc in tqdm(test_accounts):
        with HiddenPrints():
            for _ in range(DT_buy_times):
                oceantestutil.buyDT(
                    pool, DT, DT_buy_amt, funding_for_each_addr, acc, OCEAN
                )
                oceantestutil.consumeDT(DT, accounts[0], acc)

    brownie.network.chain.mine(blocks=300)  # mine 300 blocks
    print("Mining blocks")

    # give some time for subgraph to index
    print("Sleeping 30 secs")
    time.sleep(30)  # sleep little script

    FIN = len(brownie.network.chain) - 10
    # %%

    os.environ["ADDRESS_FILE"] = networkutil.chainIdToAddressFile(CHAINID)
    os.environ["SECRET_SEED"] = "123123123"
    DISPENSE_ACCT = brownie.network.accounts.add()
    os.environ["DFTOOL_KEY"] = DISPENSE_ACCT.private_key

    print("Running dftool query")
    cmd = f"./dftool query {ST} {FIN} {NSAMP} {CSV_DIR} {CHAINID}"
    os.system(cmd)

    print("Running dftool get rate")
    TOKEN_SYMBOL = "OCEAN"
    ST = "2022-01-01"
    FIN = "2022-02-02"
    cmd = f"./dftool getrate OCEAN {ST} {FIN} {CSV_DIR}"
    os.system(cmd)

    print("Running dftool calc")
    TOKEN_SYMBOL = "OCEAN"
    TOT_TOKEN = 10000.0
    cmd = f"./dftool calc {CSV_DIR} {TOT_TOKEN} {TOKEN_SYMBOL}"
    os.system(cmd)

    print("Running dftool dispense")
    TOKEN_SYMBOL = "OCEAN"
    OCEAN.transfer(DISPENSE_ACCT, TOT_TOKEN * 1e18, {"from": accounts[0]})
    df_rewards = B.DFRewards.deploy({"from": accounts[0]})
    DFREWARDS_ADDR = df_rewards.address
    TOKEN_ADDR = OCEAN.address
    cmd = f"./dftool dispense {CSV_DIR} {CHAINID} {DFREWARDS_ADDR} {TOKEN_ADDR}"
    os.system(cmd)

    claimable_amounts = []

    for acc in test_accounts:
        claimable_amounts.append(df_rewards.claimable(acc.address, OCEAN.address))

    print(claimable_amounts)
    f = open(f"{CSV_DIR}/claimable_amounts.json", "w")
    f.write(json.dumps(claimable_amounts))


main()
