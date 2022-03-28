import brownie
import os

from util import dispense
from util import oceanutil
from util.base18 import fromBase18

def test_1(ADDRESS_FILE):
    #set accounts
    oceanutil.recordDeployedContracts(ADDRESS_FILE, "development")
    test_accounts = [brownie.network.accounts[i].address for i in range(5, 10)]
    OCEAN = oceanutil.OCEANtoken()
    bal_before = {account : fromBase18(OCEAN.balanceOf(account))
                  for account in test_accounts}

    #set fake rewards
    rewards = {account : account_i * 100.0 
               for account_i, account in enumerate(test_accounts)}

    #set test file
    csv_dir = '/tmp'
    csv_file = dispense.rewardsPathToFile(csv_dir)
    if os.path.exists(csv_file):
        os.remove(csv_file)
    dispense.rewardsToCsv(rewards, csv_dir)

    #deploy contract
    dispense.deployNewContract()

    #dispense; test account balances
    dispense.dispenseRewards(csv_dir)
    for account in test_accounts:
        bal_after = fromBase18(OCEAN.balanceOf(account))
        assert (bal_before[account] - bal_after) == rewards[account]

    #dispense again; test account balances again
    dispense.dispenseRewards(csv_dir)
    for account in test_accounts:
        bal_after = fromBase18(OCEAN.balanceOf(account))
        assert (bal_before[account] - bal_after) == (rewards[account] * 2)
