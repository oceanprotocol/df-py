import pytest
from enforce_typing import enforce_types
from web3.exceptions import ContractLogicError

from df_py.util import networkutil, oceantestutil, oceanutil
from df_py.util.base18 import to_wei
from df_py.util.contract_base import ContractBase

accounts = oceantestutil.get_all_accounts()

a1 = accounts[1]
a2 = accounts[2]
a3 = accounts[3]


@enforce_types
def test_basic(w3):
    token = _deploy_token(w3, accounts[0])
    df_rewards = ContractBase(w3, "DFRewards", constructor_args=[])
    assert df_rewards.claimable(a1, token.address) == 0


@enforce_types
def test_lost_ERC20():
    # Can recover when an account accidentally sends ERC20 to DFRewards.sol?
    # test_withdrawfunc.py handles this, so no work here
    pass


@enforce_types
def test_lost_ETH():
    # Can recover when an account accidentally sends ETH to DFRewards.sol?
    # test_withdrawfunc.py handles this, so no work here
    pass


@enforce_types
def test_token(w3):
    token = _deploy_token(w3, accounts[8])
    token.transfer(accounts[0].address, to_wei(100.0), {"from": accounts[8]})

    w3.eth.default_account = accounts[0].address
    df_rewards = ContractBase(w3, "DFRewards", constructor_args=[])
    df_strategy = ContractBase(
        w3, "DFStrategyV1", constructor_args=[df_rewards.address]
    )

    tos = [a1.address, a2.address, a3.address]
    values = [10, 20, 30]
    token.approve(df_rewards, sum(values), {"from": accounts[0]})
    df_rewards.allocate(tos, values, token.address, {"from": accounts[0]})

    assert df_rewards.claimable(a1, token.address) == 10
    assert df_rewards.claimable(a2, token.address) == 20
    assert df_rewards.claimable(a3, token.address) == 30

    # a1 claims for itself
    assert token.balanceOf(a1) == 0
    df_strategy.claim([token.address], {"from": accounts[1]})
    assert token.balanceOf(a1) == 10

    # a2 claims for itself too
    assert token.balanceOf(a2) == 0
    df_strategy.claim([token.address], {"from": accounts[2]})
    assert token.balanceOf(a2) == 20

    # a9 claims for a3
    assert token.balanceOf(a3) == 0
    df_rewards.claimFor(a3, token.address, {"from": accounts[8]})
    assert token.balanceOf(a3) == 30


@enforce_types
def test_OCEAN(w3):
    oceanutil.record_dev_deployed_contracts()
    OCEAN = oceanutil.OCEAN_token(networkutil.DEV_CHAINID)
    assert OCEAN.balanceOf(accounts[0]) >= 10

    w3.eth.default_account = accounts[0].address
    df_rewards = ContractBase(w3, "DFRewards", constructor_args=[])
    df_strategy = ContractBase(
        w3, "DFStrategyV1", constructor_args=[df_rewards.address]
    )

    OCEAN.approve(df_rewards, 10, {"from": accounts[0]})
    df_rewards.allocate([a1.address], [10], OCEAN.address, {"from": accounts[0]})

    assert df_rewards.claimable(a1, OCEAN.address) == 10

    bal_before = OCEAN.balanceOf(a1)
    df_strategy.claim([OCEAN.address], {"from": accounts[1]})
    bal_after = OCEAN.balanceOf(a1)
    assert (bal_after - bal_before) == 10


@enforce_types
def test_multiple_token(w3):
    token_1 = _deploy_token(w3, accounts[0])
    token_2 = _deploy_token(w3, accounts[0])

    w3.eth.default_account = accounts[0].address
    df_rewards = ContractBase(w3, "DFRewards", constructor_args=[])
    df_strategy = ContractBase(
        w3, "DFStrategyV1", constructor_args=[df_rewards.address]
    )

    tos = [a1.address, a2.address, a3.address]
    values = [10, 20, 30]

    token_1.approve(df_rewards, sum(values), {"from": accounts[0]})
    token_2.approve(df_rewards, sum(values) + 15, {"from": accounts[0]})

    df_rewards.allocate(tos, values, token_1.address, {"from": accounts[0]})
    df_rewards.allocate(
        tos, [x + 5 for x in values], token_2.address, {"from": accounts[0]}
    )

    assert df_strategy.claimables(a1, [token_1.address, token_2.address]) == [10, 15]
    assert df_strategy.claimables(a2, [token_1.address, token_2.address]) == [20, 25]
    assert df_strategy.claimables(a3, [token_1.address, token_2.address]) == [30, 35]

    # multiple claims

    # a1 claims for itself
    assert token_1.balanceOf(a1) == 0
    assert token_2.balanceOf(a1) == 0
    df_strategy.claim([token_1.address, token_2.address], {"from": accounts[1]})
    assert token_1.balanceOf(a1) == 10
    assert token_2.balanceOf(a1) == 15

    # a2 claims for itself
    assert token_1.balanceOf(a2) == 0
    assert token_2.balanceOf(a2) == 0
    df_strategy.claim([token_1.address, token_2.address], {"from": accounts[2]})
    assert token_1.balanceOf(a2) == 20
    assert token_2.balanceOf(a2) == 25

    # a3 claims for itself
    assert token_1.balanceOf(a3) == 0
    assert token_2.balanceOf(a3) == 0
    df_strategy.claim([token_1.address, token_2.address], {"from": accounts[3]})
    assert token_1.balanceOf(a3) == 30
    assert token_2.balanceOf(a3) == 35

    # a1 can't claim extra
    assert token_1.balanceOf(a1) == 10
    assert token_2.balanceOf(a1) == 15
    df_strategy.claim([token_1.address, token_2.address], {"from": accounts[1]})
    assert token_1.balanceOf(a1) == 10
    assert token_2.balanceOf(a1) == 15


def test_bad_token(w3):
    bad_token = ContractBase(
        w3, "test/BadToken", constructor_args=["BAD", "BAD", 18, to_wei(10000.0)]
    )
    df_rewards = ContractBase(w3, "DFRewards", constructor_args=[])

    tos = [a1.address, a2.address, a3.address]
    values = [10, 20, 30]

    bad_token.approve(df_rewards, sum(values), {"from": accounts[0]})

    with pytest.raises(ContractLogicError, match="Not enough tokens"):
        df_rewards.allocate(tos, values, bad_token.address, {"from": accounts[0]})


def test_strategies(w3):
    token = _deploy_token(w3, accounts[0])

    df_rewards = ContractBase(w3, "DFRewards", constructor_args=[])
    df_strategy = ContractBase(
        w3, "test/DummyStrategy", constructor_args=[df_rewards.address]
    )

    # allocate rewards
    tos = [a1.address, a2.address, a3.address]
    values = [10, 20, 30]
    token.approve(df_rewards, sum(values), {"from": accounts[0]})
    df_rewards.allocate(tos, values, token.address, {"from": accounts[0]})

    # TODO: fix these
    assert token.balanceOf(df_strategy) == 0
    with pytest.raises(ContractLogicError, match="Caller doesn't match"):
        # tx origin must be a1
        df_strategy.claim(token.address, a1.address, {"from": accounts[2]})

    with pytest.raises(ContractLogicError, match="Caller must be a strategy"):
        # non strategy addresses cannot claim
        df_strategy.claim(token.address, a1, {"from": accounts[1]})

    # add strategy
    df_rewards.addStrategy(df_strategy.address, {"from": accounts[0]})
    assert df_rewards.isStrategy(df_strategy.address)
    assert df_rewards.live_strategies(0) == df_strategy.address

    # should claim since it's a strategy
    df_strategy.claim(token.address, a1, {"from": accounts[1]})

    # strategy balance increases
    assert token.balanceOf(df_strategy) == 10

    # should claim since it's a strategy
    df_strategy.claim(token.address, a2, {"from": accounts[2]})

    # strategy balance increases
    assert token.balanceOf(df_strategy) == 30

    # retire strategy
    df_rewards.retireStrategy(df_strategy.address, {"from": accounts[0]})
    assert not df_rewards.isStrategy(df_strategy.address)

    with pytest.raises(ContractLogicError, match="Caller must be a strategy"):
        # non strategy addresses cannot claim
        df_strategy.claim(token.address, a3, {"from": accounts[3]})

    with pytest.raises(ContractLogicError, match="Ownable: caller is not the owner"):
        # addresses other than the owner cannot add new strategy
        df_rewards.addStrategy(df_strategy.address, {"from": accounts[3]})

    # add strategy
    df_rewards.addStrategy(df_strategy.address, {"from": accounts[0]})
    assert df_rewards.isStrategy(df_strategy.address)
    assert df_rewards.live_strategies(0) == df_strategy.address

    # should claim since it's a strategy
    df_strategy.claim(token.address, a3, {"from": accounts[3]})

    # strategy balance increases
    assert token.balanceOf(df_strategy) == 60


@enforce_types
def _deploy_token(w3, account=None):
    if account:
        w3.eth.default_account = account.address

    return ContractBase(
        w3, "Simpletoken", constructor_args=["TOK", "TOK", 18, to_wei(100.0)]
    )
