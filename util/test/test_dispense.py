import brownie
import os

from util import dispense, oceanutil
from util.base18 import fromBase18, toBase18
from util.constants import BROWNIE_PROJECT as B

accounts = brownie.network.accounts
a1, a2, a3 = accounts[1].address, accounts[2].address, accounts[3].address

def test_1(ADDRESS_FILE):
    oceanutil.recordDeployedContracts(ADDRESS_FILE, "development")
    OCEAN = oceanutil.OCEANtoken()
    
    airdrop = B.Airdrop.deploy(OCEAN.address, {"from": accounts[0]})

    tos, values = [a1,a2,a3], [10,20,30]
    OCEAN.approve(airdrop, sum(values), {"from": accounts[0]})
    airdrop.allocate(tos, values, {"from": accounts[0]})
    
    assert airdrop.claimable(a1) == 10
    assert airdrop.claimable(a2) == 20
    assert airdrop.claimable(a3) == 30

    #a1 claims for itself
    bal_before = OCEAN.balanceOf(a1) 
    airdrop.claim({"from": accounts[1]})
    bal_after = OCEAN.balanceOf(a1)
    assert (bal_after - bal_before) == 10

    #a9 claims on behalf of a1
    bal_before = OCEAN.balanceOf(a3)
    airdrop.claimFor(a3, {"from": accounts[9]})
    bal_after = OCEAN.balanceOf(a3)
    assert (bal_after - bal_before) == 30    

def test_2(ADDRESS_FILE):
    #=============================================================
    #set accounts
    oceanutil.recordDeployedContracts(ADDRESS_FILE, "development")
    test_addrs = [accounts[i].address for i in range(5, 10)]
    OCEAN = oceanutil.OCEANtoken()
    bal_before = {a : fromBase18(OCEAN.balanceOf(a))
                  for a in test_addrs}

    #set fake rewards
    rewards = {addr : i*100.0 for i, addr in enumerate(test_addrs)}

    #set test file
    csv_dir = '/tmp'
    csv_file = dispense.rewardsPathToFile(csv_dir)
    if os.path.exists(csv_file):
        os.remove(csv_file)
    dispense.rewardsToCsv(rewards, csv_dir)

    #=============================================================
    #deploy contract
    OCEAN = oceanutil.OCEANtoken()
    airdrop = B.Airdrop.deploy(OCEAN.address, {"from": accounts[0]})

    #=============================================================
    #dispense, first round
    rewards = dispense.csvToRewards(csv_dir)
    tos = list(rewards.keys())
    values = [toBase18(rewards[to]) for to in tos]
    OCEAN.approve(airdrop, sum(values), {"from": accounts[0]})
    airdrop.allocate(tos, values, {"from": accounts[0]})
        
    for a in test_addrs:
        #test before claim
        bal_inc = fromBase18(OCEAN.balanceOf(a)) - bal_before[a]
        claimable = fromBase18(dispense_contract.claimable(a))
        assert bal_inc == 0.0
        assert claimable == rewards[a]

        #claim: first two accounts do it, others don't
        if a in test_addrs[:2]:
            dispense_contract.claimReward({"from": a})

        #test after claim
        bal_inc = fromBase18(OCEAN.balanceOf(a)) - bal_before[a]
        claimable = fromBase18(dispense_contract.claimable(a))
        if a in test_addrs[:2]:
            assert bal_inc == rewards[a]
            assert claimable == 0.0
        else:
            assert bal_inc == 0.0
            assert claimable == rewards[a]

    #=============================================================
    #dispense, second round
    dispense.dispenseRewards(csv_dir)
    
    for a in test_addrs:
        #test before claim
        bal_inc = fromBase18(OCEAN.balanceOf(a)) - bal_before[a]
        claimable = fromBase18(dispense_contract.claimable(a))
        if a in test_addrs[:2]:
            assert bal_inc == rewards[a]
            assert claimable == rewards[a]
        else:
            assert bal_inc == 0.0
            assert claimable == rewards[a]*2.0

        #all accounts claim
        if a in test_addrs:
            dispense_contract.claimReward({"from": a})

        #test after claim
        bal_inc = fromBase18(OCEAN.balanceOf(a)) - bal_before[a]
        claimable = fromBase18(dispense_contract.claimable(a))
        if a in test_addrs:
            assert bal_inc == rewards[a]*2.0
            assert claimable == 0.0

        
        
