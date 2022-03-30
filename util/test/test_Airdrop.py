import brownie

from util.constants import BROWNIE_PROJECT as B
from util.base18 import toBase18, fromBase18

accounts = brownie.network.accounts
a1, a2, a3 = accounts[1].address, accounts[2].address, accounts[3].address

def test_no_allocate():
    (_, airdrop) = _deployContracts(accounts[0])
    assert airdrop.claimable(a1) == 0

def test_allocate_1():
    (TOK, airdrop) = _deployContracts(accounts[0])
    to, value = a1, 0.1
    
    TOK.approve(airdrop, toBase18(value), {"from": accounts[0]})
    airdrop.allocate1(to, toBase18(value), {"from": accounts[0]})
    assert fromBase18(airdrop.claimable(a1)) == 0.1
    assert TOK.balanceOf(a1) == 0
    
    airdrop.claim({"from": accounts[1]})
    assert fromBase18(TOK.balanceOf(a1)) == 0.1

def test_allocate_many():
    a1, a2, a3 = accounts[1].address, accounts[2].address, accounts[3].address
    rewards = {a1: 0.1, a2: 0.2, a3: 0.3}
    
    TOK = B.Simpletoken.deploy(
        "TOK", "TOK", 18, toBase18(100.0), {"from": accounts[0]})
    
    airdrop = B.Airdrop.deploy(TOK.address, {"from": accounts[0]})

    assert airdrop.claimable(a1) == 0
    
    tos = list(rewards.keys())
    values = [rewards[to] for to in tos]
    assert min(values) > 0
    TOK.approve(airdrop, toBase18(sum(values)), {"from": accounts[0]})
    airdrop.allocate(tos, [toBase18(v) for v in values], {"from": accounts[0]})

    assert fromBase18(airdrop.claimable(a1)) == 0.1
    assert fromBase18(airdrop.claimable(a2)) == 0.2
    assert fromBase18(airdrop.claimable(a3)) == 0.3

    #a1 claims for itself
    assert TOK.balanceOf(a1) == 0
    airdrop.claim({"from": accounts[1]})
    assert fromBase18(TOK.balanceOf(a1)) == 0.1
    
    #a2 claims for itself too
    assert TOK.balanceOf(a2) == 0
    airdrop.claim({"from": accounts[2]})
    assert fromBase18(TOK.balanceOf(a2)) == 0.2

    #a9 claims for a3
    assert TOK.balanceOf(a3) == 0
    airdrop.claimFor(a3, {"from": accounts[9]})
    assert fromBase18(TOK.balanceOf(a3)) == 0.3

def test_allocate_thousands():
    pass

def _deployContracts(from_account):
    TOK = B.Simpletoken.deploy(
        "TOK", "TOK", 18, toBase18(100.0), {"from": from_account})
    airdrop = B.Airdrop.deploy(TOK.address, {"from": from_account})
    return (TOK, airdrop)


