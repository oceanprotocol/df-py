import brownie
from enforce_typing import enforce_types

from util.constants import BROWNIE_PROJECT as B
from util.base18 import toBase18, fromBase18

accounts = brownie.network.accounts
a1, a2, a3 = accounts[1].address, accounts[2].address, accounts[3].address


@enforce_types
def _deployTOK(account):
    return B.Simpletoken.deploy("TOK", "TOK", 18, toBase18(100.0), {"from": account})


@enforce_types
def test_transfer_eth_reverts():
    """sending native tokens to airdrop contract should revert"""
    airdrop = B.Airdrop.deploy({"from": accounts[0]})
    with brownie.reverts("Cannot send ether to nonpayable function"):
        # transfer native eth to airdrop contract
        accounts[0].transfer(airdrop, "1 ether")


@enforce_types
def test_erc20_withdraw_random():
    """owner can withdraw other erc20 tokens from the airdrop contract"""

    random_token = _deployTOK(accounts[1])

    airdrop = B.Airdrop.deploy({"from": accounts[0]})

    random_token.transfer(airdrop, toBase18(100.0), {"from": accounts[1]})

    assert random_token.balanceOf(accounts[0]) == 0

    # Withdraw random token
    airdrop.withdrawERCToken(
        toBase18(100.0), random_token.address, {"from": accounts[0]}
    )

    assert random_token.balanceOf(accounts[0]) == toBase18(100.0)


@enforce_types
def test_erc20_withdraw_main():
    """withdrawing the main token should revert"""

    TOK = _deployTOK(accounts[0])

    airdrop = B.Airdrop.deploy({"from": accounts[0]})

    TOK.transfer(airdrop, toBase18(50.0), {"from": accounts[0]})

    tos = [a1]
    values = [10]
    TOK.approve(airdrop, sum(values), {"from": accounts[0]})
    airdrop.allocate(tos, values, TOK.address, {"from": accounts[0]})

    with brownie.reverts("Cannot withdraw allocated token"):
        airdrop.withdrawERCToken(toBase18(40.0), TOK.address, {"from": accounts[0]})

    airdrop.claim([TOK.address], {"from": accounts[1]})

    airdrop.withdrawERCToken(toBase18(40.0), TOK.address, {"from": accounts[0]})
