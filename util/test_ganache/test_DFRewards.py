import time

import brownie
from brownie.network import accounts
from enforce_typing import enforce_types

from util.constants import BROWNIE_PROJECT as B
from util.base18 import fromBase18, toBase18
from util import networkutil, oceanutil


@enforce_types
def test_basic(df_rewards):
    TOK = _deployTOK(accounts[0])
    assert df_rewards.claimable(accounts[0].address, TOK.address) == 0


@enforce_types
def test_TOK(df_rewards, df_strategy):
    while len(accounts) < 5:
        accounts.add()
    accounts[0].transfer(accounts[4], toBase18(10.0))
    a1, a2, a3 = _a123()

    # main work
    TOK = _deployTOK(accounts[4])
    TOK.transfer(accounts[0], toBase18(100.0), {"from": accounts[4]})

    tos = [a1, a2, a3]
    values = [10, 20, 30]
    TOK.approve(df_rewards.address, sum(values), {"from": accounts[0]})
    df_rewards.allocate(tos, values, TOK.address, {"from": accounts[0]})

    assert df_rewards.claimable(a1, TOK.address) == 10
    assert df_rewards.claimable(a2, TOK.address) == 20
    assert df_rewards.claimable(a3, TOK.address) == 30

    # a1 claims for itself
    assert TOK.balanceOf(a1) == 0
    df_strategy.claim([TOK.address], {"from": accounts[1]})

    # a2 claims for itself too
    assert TOK.balanceOf(a2) == 0
    df_strategy.claim([TOK.address], {"from": accounts[2]})

    # a4 claims for a3
    assert TOK.balanceOf(a3) == 0
    df_rewards.claimFor(a3, TOK.address, {"from": accounts[4]})

    assert TOK.balanceOf(a1) == 10
    assert TOK.balanceOf(a2) == 20
    assert TOK.balanceOf(a3) == 30


@enforce_types
def test_OCEAN(ocean, df_rewards, df_strategy, OCEAN):
    assert OCEAN.balanceOf(accounts[0]) >= 10
    a1 = accounts[1].address

    OCEAN.approve(df_rewards.address, 10, {"from": accounts[0]})
    df_rewards.allocate([a1], [10], OCEAN.address, {"from": accounts[0]})

    assert df_rewards.claimable(a1, OCEAN.address) == 10

    bal_before = OCEAN.balanceOf(a1)
    df_strategy.claim([OCEAN.address], {"from": accounts[1]})
    bal_after = OCEAN.balanceOf(a1)
    assert (bal_after - bal_before) == 10


@enforce_types
def test_multiple_TOK(df_rewards, df_strategy):
    while len(accounts) < 5:
        accounts.add()
    a1, a2, a3 = _a123()
    accounts[0].transfer(accounts[3], toBase18(1.0))

    TOK1 = _deployTOK(accounts[0])
    TOK2 = _deployTOK(accounts[0])
    
    tos = [a1, a2, a3]
    values1 = [10, 20, 30]
    values2 = [15, 25, 35]

    TOK1.approve(df_rewards.address, sum(values1), {"from": accounts[0]})
    TOK2.approve(df_rewards.address, sum(values2), {"from": accounts[0]})

    df_rewards.allocate(tos, values1, TOK1.address, {"from": accounts[0]})
    df_rewards.allocate(tos, values2, TOK2.address, {"from": accounts[0]})

    tok1, tok2 = TOK1.address, TOK2.address
    assert df_strategy.claimables(a1, [tok1, tok2]) == [10, 15]
    assert df_strategy.claimables(a2, [tok1, tok2]) == [20, 25]
    assert df_strategy.claimables(a3, [tok1, tok2]) == [30, 35]

    # multiple claims

    # a1 claims for itself
    assert TOK1.balanceOf(a1) == 0
    assert TOK2.balanceOf(a1) == 0
    df_strategy.claim([TOK1.address, TOK2.address], {"from": accounts[1]})

    # a2 claims for itself
    assert TOK1.balanceOf(a2) == 0
    assert TOK2.balanceOf(a2) == 0
    df_strategy.claim([TOK1.address, TOK2.address], {"from": accounts[2]})

    # a3 claims for itself
    assert TOK1.balanceOf(a3) == 0
    assert TOK2.balanceOf(a3) == 0
    df_strategy.claim([TOK1.address, TOK2.address], {"from": accounts[3]})

    # now test
    assert TOK1.balanceOf(a1) == 10
    assert TOK2.balanceOf(a1) == 15
    
    assert TOK1.balanceOf(a2) == 20
    assert TOK2.balanceOf(a2) == 25
    
    assert TOK1.balanceOf(a3) == 30
    assert TOK2.balanceOf(a3) == 35

    # a1 can't claim extra
    assert TOK1.balanceOf(a1) == 10
    assert TOK2.balanceOf(a1) == 15
    df_strategy.claim([TOK1.address, TOK2.address], {"from": accounts[1]})
    assert TOK1.balanceOf(a1) == 10
    assert TOK2.balanceOf(a1) == 15


def test_strategies(df_rewards, df_strategy):
    while len(accounts) < 5:
        accounts.add()
    a1, a2, a3 = _a123()
    
    TOK = _deployTOK(accounts[0])

    # allocate rewards
    tos = [a1, a2, a3]
    values = [10, 20, 30]
    TOK.approve(df_rewards.address, sum(values), {"from": accounts[0]})
    df_rewards.allocate(tos, values, TOK.address, {"from": accounts[0]})

    assert TOK.balanceOf(df_strategy.address) == 0

    # add strategy
    df_rewards.addStrategy(df_strategy.address, {"from":accounts[0]})
    assert df_rewards.isStrategy(df_strategy.address)
    assert df_rewards.live_strategies(0) == df_strategy.address

    # retire strategy
    df_rewards.retireStrategy(df_strategy.address, {"from":accounts[0]})
    assert not df_rewards.isStrategy(df_strategy.address)


@enforce_types
def _deployTOK(account):
    return B.Simpletoken.deploy("TOK", "TOK", 18, toBase18(100.0), {"from": account})


@enforce_types
def _a123():
    accounts = brownie.network.accounts
    return accounts[1].address, accounts[2].address, accounts[3].address
