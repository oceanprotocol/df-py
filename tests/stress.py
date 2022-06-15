# %%
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
from web3 import Web3
from enforce_typing import enforce_types

from util import oceanutil, oceantestutil, networkutil, query
from util.blockrange import BlockRange
from util.constants import BROWNIE_PROJECT as B
from util.query import getApprovedTokens
from tqdm import tqdm


CHAINID = networkutil.DEV_CHAINID
ADDRESS_FILE = networkutil.chainIdToAddressFile(networkutil.DEV_CHAINID)
NUMBER_OF_ACCOUNTS = 10

w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))


def main():
    networkutil.connect(CHAINID)  # Connect to ganache
    oceanutil.recordDevDeployedContracts()  # Record deployed contract addresses on ganache

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

    approvedTokens = getApprovedTokens(networkutil.DEV_CHAINID)
    if OCEAN.address not in approvedTokens.keys():
        oceanutil.factoryRouter().addApprovedToken(OCEAN.address, {"from": accounts[0]})
        time.sleep(2)

    ## Deploy pool
    print("Deploying pool")
    (DT, pool) = oceantestutil.deployPool(5000.0, 1.0, accounts[0], OCEAN)

    ## Fund all addresses
    total_balance = OCEAN.balanceOf(accounts[0])
    STAKE_AMT = 200.0
    DT_buy_amt = 1.0
    funding_for_each_addr = (STAKE_AMT + DT_buy_amt + 50) * 1e18

    assert total_balance > funding_for_each_addr

    print(
        "Funding accounts and consuming...",
    )
    for acc in tqdm(test_accounts):
        with HiddenPrints():
            OCEAN.transfer(acc.address, funding_for_each_addr, {"from": accounts[0]})

    print("Adding stake")
    for acc in tqdm(test_accounts):
        with HiddenPrints():
            oceantestutil.addStake(pool, STAKE_AMT, acc, OCEAN)

    print("Buying and consuming DT")
    for acc in tqdm(test_accounts):
        with HiddenPrints():
            oceantestutil.buyDT(pool, DT, DT_buy_amt, funding_for_each_addr, acc, OCEAN)
            oceantestutil.consumeDT(DT, accounts[0], acc)

    # give some time for subgraph to index
    print("Sleeping 60 secs")
    time.sleep(30)  # sleep little script

    print("30 secs left")  # extra print for impatient people
    time.sleep(30)  # sleep little script

    # %%

    os.environ["ADDRESS_FILE"] = networkutil.chainIdToAddressFile(CHAINID)
    DISPENSE_ACCT = brownie.network.accounts.add()
    os.environ["DFTOOL_KEY"] = DISPENSE_ACCT.private_key

    print("Running dftool query")
    CSV_DIR = str("/tmp/df_stress_test")
    ST = 0
    FIN = "latest"
    NSAMP = 1
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

    avg_amt = sum(claimable_amounts) / len(claimable_amounts)
    print("Checking reward amount for each addresss, expected is", avg_amt)
    for amt in claimable_amounts:
        print("Expected:", avg_amt)
        print("Actual:", amt)
        assert abs(avg_amt - amt) < 1e18

    print(f"Checked {len(claimable_amounts)} addresses!")


main()
