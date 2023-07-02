import brownie
from enforce_typing import enforce_types

from df_py.util import networkutil
from df_py.util.base18 import to_wei
from df_py.util.constants import BROWNIE_PROJECT as B

accounts = None


@enforce_types
def test_transfer_eth_reverts():
    """sending native tokens to dfrewards contract should revert"""
    df_rewards = B.DFRewards.deploy({"from": accounts[0]})
    with brownie.reverts("Cannot send ether to nonpayable function"):
        # transfer native eth to dfrewards contract
        accounts[0].transfer(df_rewards, "1 ether")


@enforce_types
def test_erc20_withdraw_random():
    """owner can withdraw other erc20 tokens from the dfrewards contract"""

    random_token = _deploy_token(accounts[1])

    df_rewards = B.DFRewards.deploy({"from": accounts[0]})

    random_token.transfer(df_rewards, to_wei(100.0), {"from": accounts[1]})

    assert random_token.balanceOf(accounts[0]) == 0

    # Withdraw random token
    df_rewards.withdrawERCToken(
        to_wei(100.0), random_token.address, {"from": accounts[0]}
    )

    assert random_token.balanceOf(accounts[0]) == to_wei(100.0)


@enforce_types
def test_erc20_withdraw_main():
    """withdrawing the main token should revert"""
    token = _deploy_token(accounts[0])

    df_rewards = B.DFRewards.deploy({"from": accounts[0]})
    df_strategy = B.DFStrategyV1.deploy(df_rewards.address, {"from": accounts[0]})

    token.transfer(df_rewards, to_wei(40.0), {"from": accounts[0]})

    tos = [accounts[1].address]
    values = [to_wei(10.0)]
    token.approve(df_rewards, sum(values), {"from": accounts[0]})
    df_rewards.allocate(tos, values, token.address, {"from": accounts[0]})

    with brownie.reverts("Cannot withdraw allocated token"):
        df_rewards.withdrawERCToken(to_wei(50.0), token.address, {"from": accounts[0]})

    with brownie.reverts("Ownable: caller is not the owner"):
        df_rewards.withdrawERCToken(to_wei(20.0), token.address, {"from": accounts[1]})

    df_rewards.withdrawERCToken(to_wei(40.0), token.address, {"from": accounts[0]})
    with brownie.reverts("Cannot withdraw allocated token"):
        df_rewards.withdrawERCToken(to_wei(1.0), token.address, {"from": accounts[0]})
    df_strategy.claim([token.address], {"from": accounts[1]})

    token.transfer(df_rewards, 100, {"from": accounts[0]})
    df_rewards.withdrawERCToken(100, token.address, {"from": accounts[0]})


@enforce_types
def _deploy_token(account):
    return B.Simpletoken.deploy("TOK", "TOK", 18, to_wei(100.0), {"from": account})


@enforce_types
def setup_function():
    networkutil.connect_dev()
    global accounts
    accounts = brownie.network.accounts


@enforce_types
def teardown_function():
    brownie.network.disconnect()
