import brownie
from enforce_typing import enforce_types

from util import networkutil
from util.constants import BROWNIE_PROJECT as B
from util.base18 import toBase18

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

    random_token = _deployTOK(accounts[1])

    df_rewards = B.DFRewards.deploy({"from": accounts[0]})

    random_token.transfer(df_rewards, toBase18(100.0), {"from": accounts[1]})

    assert random_token.balanceOf(accounts[0]) == 0

    # Withdraw random token
    df_rewards.withdrawERCToken(
        toBase18(100.0), random_token.address, {"from": accounts[0]}
    )

    assert random_token.balanceOf(accounts[0]) == toBase18(100.0)


@enforce_types
def test_erc20_withdraw_main():
    """withdrawing the main token should revert"""

    TOK = _deployTOK(accounts[0])

    df_rewards = B.DFRewards.deploy({"from": accounts[0]})
    df_strategy = B.DFStrategyV1.deploy(df_rewards.address, {"from": accounts[0]})

    TOK.transfer(df_rewards, toBase18(40.0), {"from": accounts[0]})

    tos = [accounts[1].address]
    values = [toBase18(10.0)]
    TOK.approve(df_rewards, sum(values), {"from": accounts[0]})
    df_rewards.allocate(tos, values, TOK.address, {"from": accounts[0]})

    with brownie.reverts("Cannot withdraw allocated token"):
        df_rewards.withdrawERCToken(toBase18(50.0), TOK.address, {"from": accounts[0]})

    with brownie.reverts("Ownable: caller is not the owner"):
        df_rewards.withdrawERCToken(toBase18(20.0), TOK.address, {"from": accounts[1]})

    df_rewards.withdrawERCToken(toBase18(40.0), TOK.address, {"from": accounts[0]})
    with brownie.reverts("Cannot withdraw allocated token"):
        df_rewards.withdrawERCToken(toBase18(1.0), TOK.address, {"from": accounts[0]})
    df_strategy.claim([TOK.address], {"from": accounts[1]})

    TOK.transfer(df_rewards, 100, {"from": accounts[0]})
    df_rewards.withdrawERCToken(100, TOK.address, {"from": accounts[0]})


@enforce_types
def _deployTOK(account):
    return B.Simpletoken.deploy("TOK", "TOK", 18, toBase18(100.0), {"from": account})


@enforce_types
def setup_function():
    networkutil.connect(networkutil.DEV_CHAINID)
    global accounts
    accounts = brownie.network.accounts


@enforce_types
def teardown_function():
    brownie.network.disconnect()
