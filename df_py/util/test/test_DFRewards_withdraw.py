import os

import pytest
from enforce_typing import enforce_types
from eth_account import Account
from web3.exceptions import ContractLogicError

from df_py.util.base18 import to_wei
from df_py.util.contract_base import ContractBase
from df_py.util.networkutil import send_ether

accounts = [
    Account.from_key(private_key=os.getenv(f"TEST_PRIVATE_KEY{index}"))
    for index in range(0, 9)
]


@enforce_types
def test_transfer_eth_reverts(w3):
    """sending native tokens to dfrewards contract should revert"""
    df_rewards = ContractBase(w3, "DFRewards", constructor_args=[])

    with pytest.raises(ContractLogicError):
        # transfer native eth to dfrewards contract
        send_ether(w3, accounts[0], df_rewards.address, to_wei(1))


@enforce_types
def test_erc20_withdraw_random(w3):
    """owner can withdraw other erc20 tokens from the dfrewards contract"""

    random_token = _deploy_token(w3, accounts[1])

    w3.eth.default_account = accounts[0].address
    df_rewards = ContractBase(w3, "DFRewards", constructor_args=[])

    random_token.transfer(df_rewards, to_wei(100.0), {"from": accounts[1]})

    assert random_token.balanceOf(accounts[0]) == 0

    # Withdraw random token
    df_rewards.withdrawERCToken(
        to_wei(100.0), random_token.address, {"from": accounts[0]}
    )

    assert random_token.balanceOf(accounts[0]) == to_wei(100.0)


@enforce_types
def test_erc20_withdraw_main(w3):
    """withdrawing the main token should revert"""
    token = _deploy_token(w3, accounts[0])

    w3.eth.default_account = accounts[0].address
    df_rewards = ContractBase(w3, "DFRewards", constructor_args=[])
    df_strategy = ContractBase(
        w3, "DFStrategyV1", constructor_args=[df_rewards.address]
    )

    token.transfer(df_rewards, to_wei(40.0), {"from": accounts[0]})

    tos = [accounts[1].address]
    values = [to_wei(10.0)]
    token.approve(df_rewards, sum(values), {"from": accounts[0]})
    df_rewards.allocate(tos, values, token.address, {"from": accounts[0]})

    with pytest.raises(ContractLogicError, match="Cannot withdraw allocated token"):
        df_rewards.withdrawERCToken(to_wei(50.0), token.address, {"from": accounts[0]})

    with pytest.raises(ContractLogicError, match="Ownable: caller is not the owner"):
        df_rewards.withdrawERCToken(to_wei(20.0), token.address, {"from": accounts[1]})

    df_rewards.withdrawERCToken(to_wei(40.0), token.address, {"from": accounts[0]})
    with pytest.raises(ContractLogicError, match="Cannot withdraw allocated token"):
        df_rewards.withdrawERCToken(to_wei(1.0), token.address, {"from": accounts[0]})
    df_strategy.claim([token.address], {"from": accounts[1]})

    token.transfer(df_rewards, 100, {"from": accounts[0]})
    df_rewards.withdrawERCToken(100, token.address, {"from": accounts[0]})


@enforce_types
def _deploy_token(w3, account):
    if account:
        w3.eth.default_account = account.address

    return ContractBase(
        w3, "Simpletoken", constructor_args=["TOK", "TOK", 18, to_wei(100.0)]
    )
