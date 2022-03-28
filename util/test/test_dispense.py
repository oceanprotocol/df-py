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
    bal_before = {a : fromBase18(OCEAN.balanceOf(a))
                  for a in test_accounts}

    #set fake rewards
    rewards = {a : i*100.0 for i, a in enumerate(test_accounts)}

    #set test file
    csv_dir = '/tmp'
    csv_file = dispense.rewardsPathToFile(csv_dir)
    if os.path.exists(csv_file):
        os.remove(csv_file)
    dispense.rewardsToCsv(rewards, csv_dir)

    #deploy contract
    airdrop_contract = dispense.deployAirdropContract()

    #=============================================================
    #dispense, first round
    merkle_root = FIXME
    total_allocation = sum(rewards.values())
    assert fromBase18(OCEAN.balanceOf(accounts[0])) >= total_allocation
    
    airdrop_contract.seedNewAllocations(
        merkle_root, toBase18(total_allocation), {"from": accounts[0]})
    
    dispense.dispenseRewards(csv_dir, accounts[0])
    
        
    for a in test_accounts:
        #test before claim
        bal_inc = fromBase18(OCEAN.balanceOf(a)) - bal_before[a]
        claimable = fromBase18(dispense_contract.claimable(a))
        assert bal_inc == 0.0
        assert fromBase18(dispense_contract.claimable(at)) == rewards[a]

        #claim: first two accounts do it, others don't
        if a in test_accounts[:2]:
            dispense_contract.claimReward({"from": a})

        #test after claim
        bal_inc = fromBase18(OCEAN.balanceOf(a)) - bal_before[a]
        claimable = fromBase18(dispense_contract.claimable(a))
        if a in test_accounts[:2]:
            assert bal_inc == rewards[a]
            assert claimable == 0.0
        else:
            assert bal_inc == 0.0
            assert claimable == rewards[a]

    #=============================================================
    #dispense, second round
    dispense.dispenseRewards(csv_dir)
    
    for a in test_accounts:
        #test before claim
        bal_inc = fromBase18(OCEAN.balanceOf(a)) - bal_before[a]
        claimable = fromBase18(dispense_contract.claimable(a))
        if a in test_accounts[:2]:
            assert bal_inc == rewards[a]
            assert claimable == rewards[a]
        else:
            assert bal_inc == 0.0
            assert claimable == rewards[a]*2.0

        #all accounts claim
        if a in test_accounts:
            dispense_contract.claimReward({"from": a})

        #test after claim
        bal_inc = fromBase18(OCEAN.balanceOf(a)) - bal_before[a]
        claimable = fromBase18(dispense_contract.claimable(a))
        if a in test_accounts:
            assert bal_inc == rewards[a]*2.0
            assert claimable == 0.0

        
        
