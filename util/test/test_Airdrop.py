import brownie

from util.constants import BROWNIE_PROJECT as B
from util.base18 import toBase18, fromBase18
from util import oceanutil

accounts = brownie.network.accounts
a1, a2, a3 = accounts[1].address, accounts[2].address, accounts[3].address

def test_basic():
    TOK = _deployTOK(accounts[0])
    airdrop = B.Airdrop.deploy(TOK.address, {"from": accounts[0]})
    assert airdrop.getToken() == TOK.address
    assert airdrop.claimable(a1) == 0

def test_TOK():
    TOK = _deployTOK(accounts[9])
    TOK.transfer(accounts[0].address, toBase18(100.0), {"from": accounts[9]})
    
    airdrop = B.Airdrop.deploy(TOK.address, {"from": accounts[0]})
        
    tos = [a1, a2, a3]
    values = [10, 20, 30]
    TOK.approve(airdrop, sum(values), {"from": accounts[0]})
    airdrop.allocate(tos, values, {"from": accounts[0]})
    
    assert airdrop.claimable(a1) == 10
    assert airdrop.claimable(a2) == 20
    assert airdrop.claimable(a3) == 30

    #a1 claims for itself
    assert TOK.balanceOf(a1) == 0
    airdrop.claim({"from": accounts[1]})
    assert TOK.balanceOf(a1) == 10
    
    #a2 claims for itself too
    assert TOK.balanceOf(a2) == 0
    airdrop.claim({"from": accounts[2]})
    assert TOK.balanceOf(a2) == 20

    #a9 claims for a3
    assert TOK.balanceOf(a3) == 0
    airdrop.claimFor(a3, {"from": accounts[9]})
    assert TOK.balanceOf(a3) == 30

def test_OCEAN(ADDRESS_FILE):
    oceanutil.recordDeployedContracts(ADDRESS_FILE, "development")
    OCEAN = oceanutil.OCEANtoken()
    assert OCEAN.balanceOf(accounts[0]) >= 10
    
    airdrop = B.Airdrop.deploy(OCEAN.address, {"from": accounts[0]})
        
    OCEAN.approve(airdrop, 10, {"from": accounts[0]})
    airdrop.allocate([a1], [10], {"from": accounts[0]})
    
    assert airdrop.claimable(a1) == 10

    bal_before = OCEAN.balanceOf(a1)
    airdrop.claim({"from": accounts[1]})
    bal_after = OCEAN.balanceOf(a1)
    assert (bal_after - bal_before) == 10    

def _deployTOK(account):
    return B.Simpletoken.deploy(
        "TOK", "TOK", 18, toBase18(100.0), {"from": account})
    

