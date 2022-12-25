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

    # workaround if ganache txs not done yet
    for i in range(10):
        if TOK.balanceOf(a3) > 0:
            break
        time.sleep(0.5)
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
    tx = df_strategy.claim([OCEAN.address], {"from": accounts[1]})
    for i in range(10):
        if OCEAN.balanceOf(a1) > bal_before:
            break
        time.sleep(0.5)
    bal_after = OCEAN.balanceOf(a1)
    assert (bal_after - bal_before) == 10


@enforce_types
def test_multiple_TOK(df_rewards, df_strategy):
    while len(accounts) < 5:
        accounts.add()
    a1, a2, a3 = _a123()

    TOK1 = _deployTOK(accounts[0])
    TOK2 = _deployTOK(accounts[0])
    
    tos = [a1, a2, a3]
    values = [10, 20, 30]

    TOK1.approve(df_rewards.address, sum(values), {"from": accounts[0]})
    TOK2.approve(df_rewards.address, sum(values) + 15, {"from": accounts[0]})

    df_rewards.allocate(tos, values, TOK1.address, {"from": accounts[0]})
    df_rewards.allocate(
        tos, [x + 5 for x in values], TOK2.address, {"from": accounts[0]}
    )

    t1, t2 = TOK1.address, TOK2.address
    assert df_strategy.claimables(a1, [t1, t2]) == [10, 15]
    assert df_strategy.claimables(a2, [t1, t2]) == [20, 25]
    assert df_strategy.claimables(a3, [t1, t2]) == [30, 35]

    # multiple claims

    # a1 claims for itself
    assert TOK1.balanceOf(a1) == 0
    assert TOK2.balanceOf(a1) == 0
    df_strategy.claim([TOK1.address, TOK2.address], {"from": accounts[1]})
    assert TOK1.balanceOf(a1) == 10
    assert TOK2.balanceOf(a1) == 15

    # a2 claims for itself
    assert TOK1.balanceOf(a2) == 0
    assert TOK2.balanceOf(a2) == 0
    df_strategy.claim([TOK1.address, TOK2.address], {"from": accounts[2]})
    assert TOK1.balanceOf(a2) == 20
    assert TOK2.balanceOf(a2) == 25

    # a3 claims for itself
    assert TOK1.balanceOf(a3) == 0
    assert TOK2.balanceOf(a3) == 0
    df_strategy.claim([TOK1.address, TOK2.address], {"from": accounts[3]})
    assert TOK1.balanceOf(a3) == 30
    assert TOK2.balanceOf(a3) == 35

    # a1 can't claim extra
    assert TOK1.balanceOf(a1) == 10
    assert TOK2.balanceOf(a1) == 15
    df_strategy.claim([TOK1.address, TOK2.address], {"from": accounts[1]})
    assert TOK1.balanceOf(a1) == 10
    assert TOK2.balanceOf(a1) == 15


def test_bad_token(ocean, df_rewards):
    while len(accounts) < 5:
        accounts.add()
    a1, a2, a3 = _a123()
    
    badToken = B.Badtoken.deploy(
        "BAD", "BAD", 18, toBase18(10000.0), {"from": accounts[0]}
    )

    tos = [a1, a2, a3]
    values = [10, 20, 30]

    badToken.approve(df_rewards.address, sum(values), {"from": accounts[0]})

    with brownie.reverts("Not enough tokens"):
        df_rewards.allocate(tos, values, badToken.address, {"from": accounts[0]})


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

    assert TOK.balanceOf(df_strategy) == 0
    with brownie.reverts("Caller doesn't match"):
        # tx origin must be a1
        df_strategy.claim(TOK.address, a1, {"from": accounts[2]})

    with brownie.reverts("Caller must be a strategy"):
        # non strategy addresses cannot claim
        df_strategy.claim(TOK.address, a1, {"from": accounts[1]})

    # add strategy
    df_rewards.addStrategy(df_strategy.address)
    assert df_rewards.isStrategy(df_strategy.address)
    assert df_rewards.live_strategies(0) == df_strategy.address

    # should claim since it's a strategy
    df_strategy.claim(TOK.address, a1, {"from": accounts[1]})

    # strategy balance increases
    assert TOK.balanceOf(df_strategy) == 10

    # should claim since it's a strategy
    df_strategy.claim(TOK.address, a2, {"from": accounts[2]})

    # strategy balance increases
    assert TOK.balanceOf(df_strategy) == 30

    # retire strategy
    df_rewards.retireStrategy(df_strategy.address)
    assert not df_rewards.isStrategy(df_strategy.address)

    with brownie.reverts("Caller must be a strategy"):
        # non strategy addresses cannot claim
        df_strategy.claim(TOK.address, a3, {"from": accounts[3]})

    with brownie.reverts("Ownable: caller is not the owner"):
        # addresses other than the owner cannot add new strategy
        df_rewards.addStrategy(df_strategy.address, {"from": accounts[3]})

    # add strategy
    df_rewards.addStrategy(df_strategy.address)
    assert df_rewards.isStrategy(df_strategy.address)
    assert df_rewards.live_strategies(0) == df_strategy.address

    # should claim since it's a strategy
    df_strategy.claim(TOK.address, a3, {"from": accounts[3]})

    # strategy balance increases
    assert TOK.balanceOf(df_strategy) == 60



@enforce_types
def _deployTOK(account):
    return B.Simpletoken.deploy("TOK", "TOK", 18, toBase18(100.0), {"from": account})


@enforce_types
def _a123():
    accounts = brownie.network.accounts
    return accounts[1].address, accounts[2].address, accounts[3].address
