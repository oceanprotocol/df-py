import brownie
import os
import pytest

from util import dispense, oceanutil
from util.base18 import fromBase18, toBase18
from util.constants import BROWNIE_PROJECT as B

accounts = brownie.network.accounts
a1, a2, a3 = accounts[1].address, accounts[2].address, accounts[3].address

def test_csv():
    rewards = {a1:0.1, a2:0.2, a3:0.3}
    
    csv_dir = '/tmp'
    csv_file = dispense.rewardsPathToFile(csv_dir)
    if os.path.exists(csv_file):
        os.remove(csv_file)
        
    dispense.rewardsToCsv(rewards, csv_dir)

    rewards2 = dispense.csvToRewards(csv_dir)

    assert rewards == rewards2

def test_1(ADDRESS_FILE):
    oceanutil.recordDeployedContracts(ADDRESS_FILE, "development")
    OCEAN = oceanutil.OCEANtoken()
    airdrop = B.Airdrop.deploy(OCEAN.address, {"from": accounts[0]})

    rewards = {a1:0.1, a2:0.2, a3:0.3}
    
    tos = list(rewards.keys())
    values = [toBase18(rewards[to]) for to in tos]
    
    OCEAN.approve(airdrop, sum(values), {"from": accounts[0]})
    airdrop.allocate(tos, values, {"from": accounts[0]})
    
    assert fromBase18(airdrop.claimable(a1)) == 0.1
    assert fromBase18(airdrop.claimable(a2)) == 0.2
    assert fromBase18(airdrop.claimable(a3)) == 0.3

    #a1 claims for itself
    bal_before = fromBase18(OCEAN.balanceOf(a1))
    airdrop.claim({"from": accounts[1]})
    bal_after = fromBase18(OCEAN.balanceOf(a1))
    assert (bal_after - bal_before) == pytest.approx(0.1)

    #a9 claims on behalf of a1
    bal_before = fromBase18(OCEAN.balanceOf(a3))
    airdrop.claimFor(a3, {"from": accounts[9]})
    bal_after = fromBase18(OCEAN.balanceOf(a3))
    assert (bal_after - bal_before) == pytest.approx(0.3)

