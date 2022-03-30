import brownie

from util.constants import BROWNIE_PROJECT0812 as B
from util.base18 import toBase18, fromBase18

accounts = brownie.network.accounts

def test_1():
    rewards = {accounts[1].address : 0.1,
               accounts[2].address : 0.2}
    
    TOK = B.Simpletoken.deploy(
        "TOK", "TOK", 18, toBase18(100.0), {"from": accounts[0]})
    
    airdrop_contract = B.Airdrop.deploy(TOK)
    TOK.approve(airdrop_contract, toBase18(10.0), {"from": accounts[0]})

    tos = list(rewards.keys())
    values = [rewards[to] for to in tos]
    airdrop_contract.allocate(tos, values, "from": accounts[0]})

def test_10K_recipients():
    pass
