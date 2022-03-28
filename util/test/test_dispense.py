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
    balances_before = {account : fromBase18(OCEAN.balanceOf(account))
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

    #**MAIN WORK: call dispense**
    dispense.dispenseRewards(csv_dir)

    #did dispense work?
    for account in test_accounts:
        bal_before = balances_before[account]
        bal_after = fromBase18(OCEAN.balanceOf(account))
        exp_reward = rewards[account]
        assert (bal_before + exp_reward) == bal_after
                               
