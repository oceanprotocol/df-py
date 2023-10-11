from enforce_typing import enforce_types

from df_py.util.base18 import to_wei
from df_py.util.contract_base import ContractBase


@enforce_types
def test_transfer(w3, all_accounts):
    accounts = all_accounts
    token = _deploy_token(w3)
    initial_balance = token.balanceOf(accounts[0])
    assert token.totalSupply() == to_wei(1e21)
    token.transfer(accounts[1], to_wei(1e20), {"from": accounts[0]})
    assert token.balanceOf(accounts[1]) == to_wei(1e20)
    assert token.balanceOf(accounts[0]) == initial_balance - to_wei(1e20)


@enforce_types
def test_approve(w3, all_accounts):
    accounts = all_accounts
    token = _deploy_token(w3)
    token.approve(accounts[1], to_wei(1e19), {"from": accounts[0]})
    assert token.allowance(accounts[0], accounts[1]) == to_wei(1e19)
    assert token.allowance(accounts[0], accounts[2]) == 0

    token.approve(accounts[1], to_wei(6e18), {"from": accounts[0]})
    assert token.allowance(accounts[0], accounts[1]) == to_wei(6e18)


@enforce_types
def test_transferFrom(w3, all_accounts):
    accounts = all_accounts
    token = _deploy_token(w3)
    initial_balance = token.balanceOf(accounts[0])

    token.approve(accounts[1], to_wei(6e18), {"from": accounts[0]})
    token.transferFrom(accounts[0], accounts[2], to_wei(5e18), {"from": accounts[1]})

    assert token.balanceOf(accounts[2]) == to_wei(5e18)
    assert token.balanceOf(accounts[1]) == 0

    assert token.balanceOf(accounts[0]) == initial_balance - to_wei(5e18)


@enforce_types
def _deploy_token(w3):
    return ContractBase(
        w3, "Simpletoken", constructor_args=["TST", "Test Token", 18, to_wei(1e21)]
    )
