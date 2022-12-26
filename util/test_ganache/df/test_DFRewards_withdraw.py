import brownie
from brownie.network import accounts
from enforce_typing import enforce_types

from util import networkutil
from util.constants import BROWNIE_PROJECT as B
from util.base18 import fromBase18, toBase18


@enforce_types
def test_withdraw_random_TOK(df_rewards):
    """owner can withdraw other erc20 tokens from the dfrewards contract"""

    TOK = _deployTOK(accounts[1])

    TOK.transfer(df_rewards.address, toBase18(100.0), {"from": accounts[1]})

    assert TOK.balanceOf(accounts[0]) == 0

    df_rewards.withdrawERCToken(
        toBase18(100.0), TOK.address, {"from": accounts[0]}
    )

    import time
    timeout = time.time() + 10
    while time.time() < timeout and not (fromBase18(TOK.balanceOf(accounts[0])) == 100.0):
        time.sleep(0.5)
    assert fromBase18(TOK.balanceOf(accounts[0])) == 100.0


@enforce_types
def test_withdraw_main(df_rewards, df_strategy):
    TOK = _deployTOK(accounts[0])

    TOK.transfer(df_rewards.address, toBase18(40.0), {"from": accounts[0]})

    tos = [accounts[1].address]
    values = [toBase18(10.0)]
    TOK.approve(df_rewards.address, sum(values), {"from": accounts[0]})
    df_rewards.allocate(tos, values, TOK.address, {"from": accounts[0]})

    df_rewards.withdrawERCToken(toBase18(40.0), TOK.address, {"from": accounts[0]})

    df_strategy.claim([TOK.address], {"from": accounts[1]})

    TOK.transfer(df_rewards.address, 100, {"from": accounts[0]})
    df_rewards.withdrawERCToken(100, TOK.address, {"from": accounts[0]})


@enforce_types
def _deployTOK(account):
    return B.Simpletoken.deploy("TOK", "TOK", 18, toBase18(100.0), {"from": account})


# IDEA: maybe setup_function and teardown_function are the key way
# to avoid reproducability issues

# @enforce_types
# def setup_function():
#     networkutil.connect(networkutil.DEV_CHAINID)
#     global accounts
#     accounts = brownie.network.accounts


# @enforce_types
# def teardown_function():
#     brownie.network.disconnect()
