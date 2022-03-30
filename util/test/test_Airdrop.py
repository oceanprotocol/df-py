import brownie

from util.constants import BROWNIE_PROJECT as B
from util.base18 import toBase18, fromBase18

accounts = brownie.network.accounts

def test_1():
    a1, a2, a3 = accounts[1].address, accounts[2].address, accounts[3].address
    rewards = {a1: 0.1, a2: 0.2, a3: 0.3}
    
    TOK = B.Simpletoken.deploy(
        "TOK", "TOK", 18, toBase18(100.0), {"from": accounts[0]})
    
    airdrop_contract = B.Airdrop.deploy(TOK.address, {"from": accounts[0]})

    assert airdrop_contract.claimable(a1) == 0
    
    tos = list(rewards.keys())
    values = [toBase18(rewards[to]) for to in tos]
    assert min(values) > 0
    TOK.approve(airdrop_contract, toBase18(sum(values)), {"from": accounts[0]})
    airdrop_contract.allocate(tos, values, {"from": accounts[0]})

    assert fromBase18(airdrop_contract.claimable(a1)) == 0.1
    assert fromBase18(airdrop_contract.claimable(a2)) == 0.2
    assert fromBase18(airdrop_contract.claimable(a3)) == 0.3

    #a1 claims for itself
    assert TOK.balanceOf(a1) == 0
    airdrop_contract.claim({"from": accounts[1]})
    assert fromBase18(TOK.balanceOf(a1)) == 0.1
    
    #a2 claims for itself too
    assert TOK.balanceOf(a2) == 0
    airdrop_contract.claim({"from": accounts[2]})
    assert fromBase18(TOK.balanceOf(a2)) == 0.2

    #a9 claims for a3
    assert TOK.balanceOf(a3) == 0
    airdrop_contract.claim(a3, {"from": accounts[9]})
    assert fromBase18(TOK.balanceOf(a3)) == 0.3

def test_10K_recipients():
    pass
