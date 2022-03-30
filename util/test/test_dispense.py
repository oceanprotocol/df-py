import brownie
import os
import pytest

from util import dispense
from util.oceanutil import recordDeployedContracts, OCEANtoken
from util.base18 import fromBase18, toBase18
from util.constants import BROWNIE_PROJECT as B

accounts = brownie.network.accounts
a1, a2, a3 = accounts[1].address, accounts[2].address, accounts[3].address

def test_csv():
    rewards = {a1:0.1, a2:0.2, a3:0.3}
    _rewardsToCsvWithRemove(rewards, '/tmp')
    (tos, values_float, values_int) = dispense.csvToRewardsLists('/tmp')
    assert len(tos) == len(values_float) == len(values_int)
    assert rewards == {to:value_f for to,value_f in zip(tos, values_float)} 
    assert values_float == [fromBase18(value_int) for value_int in values_int]

def test_main(ADDRESS_FILE):
    recordDeployedContracts(ADDRESS_FILE, "development")
    OCEAN = OCEANtoken()

    rewards = {a1:0.1, a2:0.2, a3:0.3}
    _rewardsToCsvWithRemove(rewards, '/tmp')    

    airdrop = B.Airdrop.deploy(OCEAN.address, {"from": accounts[0]})
    
    dispense.dispenseRewards('/tmp', airdrop.address, accounts[0])

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

def _rewardsToCsvWithRemove(rewards, csv_dir):
    csv_file = dispense.rewardsPathToFile(csv_dir)
    if os.path.exists(csv_file):
        os.remove(csv_file)
    dispense.rewardsToCsv(rewards, csv_dir)
    return csv_file
