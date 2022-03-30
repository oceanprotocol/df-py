import brownie

from util.constants import BROWNIE_PROJECT as B
from util.base18 import toBase18, fromBase18

accounts = brownie.network.accounts
a1, a2, a3 = accounts[1].address, accounts[2].address, accounts[3].address

def test_no_allocate():
    (_, airdrop) = _deployContracts(accounts[0])
    assert airdrop.claimable(a1) == 0

def test_allocate_many():
    (TOK, airdrop) = _deployContracts(accounts[0])
        
    tos = [a1, a2, a3]
    values = [10, 20, 30]
    TOK.approve(airdrop, 10+20+30, {"from": accounts[0]})
    airdrop.allocate(tos, values, {"from": accounts[0]})

    brownie.network.chain.mine(blocks=2)
    
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

def test_allocate_thousands():
    pass

def _deployContracts(from_account):
    TOK = B.Simpletoken.deploy(
        "TOK", "TOK", 18, toBase18(100.0), {"from": from_account})
    airdrop = B.Airdrop.deploy(TOK.address, {"from": from_account})
    return (TOK, airdrop)


