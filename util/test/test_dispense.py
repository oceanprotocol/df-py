import brownie
from enforce_typing import enforce_types
import os
import pytest

from util import dispense
from util.oceanutil import recordDeployedContracts, OCEANtoken
from util.base18 import fromBase18, toBase18
from util.constants import BROWNIE_PROJECT as B

accounts = brownie.network.accounts
a1, a2, a3 = accounts[1].address, accounts[2].address, accounts[3].address

@enforce_types
def test_csv():
    rewards = {a1:0.1, a2:0.2, a3:0.3}
    _saveRewardsCsvWithRemove(rewards, '/tmp')
    (tos, values_float, values_int) = dispense.loadRewardsCsv('/tmp')
    assert len(tos) == len(values_float) == len(values_int)
    assert rewards == {to:value_f for to,value_f in zip(tos, values_float)} 
    assert values_float == [fromBase18(value_int) for value_int in values_int]

@enforce_types
def test_dispenseWithCsv(ADDRESS_FILE):
    recordDeployedContracts(ADDRESS_FILE, "development")
    OCEAN = OCEANtoken()

    airdrop = B.Airdrop.deploy(OCEAN.address, {"from": accounts[0]})
    
    rewards = {a1:0.1, a2:0.2, a3:0.3}
    csv_dir = '/tmp'
    _saveRewardsCsvWithRemove(rewards, csv_dir)

    (tos, _, values_int) = loadRewardsCsv(csv_dir)
    dispenseFromLists(tos, values_int, airdrop.address, accounts[0])

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

@enforce_types
def test_dispenseFromLists_with_batching(ADDRESS_FILE):
    recordDeployedContracts(ADDRESS_FILE, "development")
    OCEAN = OCEANtoken()
    
    airdrop = B.Airdrop.deploy(OCEAN.address, {"from": accounts[0]})

    batch_size = 3
    N = batch_size * 3 + 1 #enough accounts to ensure batching
    assert len(accounts) >= N
    tos = [accounts[i] for i in range(N)]
    values_int = [toBase18(i+1.0) for i in range(N)]
    
    dispense.dispenseFromLists(
        tos, values_int, airdrop.address, accounts[0], batch_size=batch_size)

@enforce_types
def _saveRewardsCsvWithRemove(rewards:dict, csv_dir:str):
    csv_file = dispense.rewardsPathToFile(csv_dir)
    if os.path.exists(csv_file):
        os.remove(csv_file)
    dispense.saveRewardsCsv(rewards, csv_dir)
    return csv_file
