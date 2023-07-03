import brownie
from enforce_typing import enforce_types

from df_py.util import networkutil, oceanutil
from df_py.util.base18 import to_wei
from df_py.util.constants import BROWNIE_PROJECT as B

accounts, a1, a2, a3 = None, None, None, None


@enforce_types
def test_basic():
    token = _deploy_token(accounts[0])
    df_rewards = B.DFRewards.deploy({"from": accounts[0]})
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
def test_token():
    token = _deploy_token(accounts[9])
    token.transfer(accounts[0].address, to_wei(100.0), {"from": accounts[9]})

    df_rewards = B.DFRewards.deploy({"from": accounts[0]})
    df_strategy = B.DFStrategyV1.deploy(df_rewards.address, {"from": accounts[0]})

    tos = [a1, a2, a3]
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
    df_rewards.claimFor(a3, token.address, {"from": accounts[9]})
    assert token.balanceOf(a3) == 30


@enforce_types
def test_OCEAN():
    address_file = networkutil.chain_id_to_address_file(networkutil.DEV_CHAINID)
    oceanutil.record_deployed_contracts(address_file)
    OCEAN = oceanutil.OCEAN_token()
    assert OCEAN.balanceOf(accounts[0]) >= 10

    df_rewards = B.DFRewards.deploy({"from": accounts[0]})
    df_strategy = B.DFStrategyV1.deploy(df_rewards.address, {"from": accounts[0]})

    OCEAN.approve(df_rewards, 10, {"from": accounts[0]})
    df_rewards.allocate([a1], [10], OCEAN.address, {"from": accounts[0]})

    assert df_rewards.claimable(a1, OCEAN.address) == 10

    bal_before = OCEAN.balanceOf(a1)
    df_strategy.claim([OCEAN.address], {"from": accounts[1]})
    bal_after = OCEAN.balanceOf(a1)
    assert (bal_after - bal_before) == 10


@enforce_types
def test_multiple_token():
    token_1 = _deploy_token(accounts[0])
    token_2 = _deploy_token(accounts[0])

    df_rewards = B.DFRewards.deploy({"from": accounts[0]})
    df_strategy = B.DFStrategyV1.deploy(df_rewards.address, {"from": accounts[0]})

    tos = [a1, a2, a3]
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


def test_bad_token():
    bad_token = B.Badtoken.deploy(
        "BAD", "BAD", 18, to_wei(10000.0), {"from": accounts[0]}
    )
    df_rewards = B.DFRewards.deploy({"from": accounts[0]})

    tos = [a1, a2, a3]
    values = [10, 20, 30]

    bad_token.approve(df_rewards, sum(values), {"from": accounts[0]})

    with brownie.reverts("Not enough tokens"):
        df_rewards.allocate(tos, values, bad_token.address, {"from": accounts[0]})


def test_strategies():
    token = _deploy_token(accounts[0])

    df_rewards = B.DFRewards.deploy({"from": accounts[0]})
    df_strategy = B.DummyStrategy.deploy(df_rewards.address, {"from": accounts[0]})

    # allocate rewards
    tos = [a1, a2, a3]
    values = [10, 20, 30]
    token.approve(df_rewards, sum(values), {"from": accounts[0]})
    df_rewards.allocate(tos, values, token.address, {"from": accounts[0]})

    assert token.balanceOf(df_strategy) == 0
    with brownie.reverts("Caller doesn't match"):
        # tx origin must be a1
        df_strategy.claim(token.address, a1, {"from": accounts[2]})

    with brownie.reverts("Caller must be a strategy"):
        # non strategy addresses cannot claim
        df_strategy.claim(token.address, a1, {"from": accounts[1]})

    # add strategy
    df_rewards.addStrategy(df_strategy.address)
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
    df_rewards.retireStrategy(df_strategy.address)
    assert not df_rewards.isStrategy(df_strategy.address)

    with brownie.reverts("Caller must be a strategy"):
        # non strategy addresses cannot claim
        df_strategy.claim(token.address, a3, {"from": accounts[3]})

    with brownie.reverts("Ownable: caller is not the owner"):
        # addresses other than the owner cannot add new strategy
        df_rewards.addStrategy(df_strategy.address, {"from": accounts[3]})

    # add strategy
    df_rewards.addStrategy(df_strategy.address)
    assert df_rewards.isStrategy(df_strategy.address)
    assert df_rewards.live_strategies(0) == df_strategy.address

    # should claim since it's a strategy
    df_strategy.claim(token.address, a3, {"from": accounts[3]})

    # strategy balance increases
    assert token.balanceOf(df_strategy) == 60


@enforce_types
def _test_claim_and_restake():
    address_file = networkutil.chain_id_to_address_file(networkutil.DEV_CHAINID)
    oceanutil.record_deployed_contracts(address_file)
    OCEAN = oceanutil.OCEAN_token()
    deployer = accounts[0]
    bob = accounts[1]

    OCEAN.transfer(bob, 100, {"from": deployer})

    df_rewards = B.DFRewards.deploy({"from": deployer})
    df_strategy = B.DFStrategyV1.deploy(df_rewards.address, {"from": deployer})
    df_rewards.addStrategy(df_strategy.address)

    veOCEAN = B.veOcean.deploy(
        OCEAN.address, "veOCEAN", "veOCEAN", "0.1.0", {"from": deployer}
    )

    OCEAN.approve(veOCEAN.address, 100, {"from": bob})
    unlock_time = brownie.network.chain.time() + 14 * 86400
    veOCEAN.create_lock(100, unlock_time, {"from": bob})

    tos = [a1]
    values = [50]
    OCEAN.approve(df_rewards, sum(values), {"from": deployer})
    df_rewards.allocate(tos, values, OCEAN.address, {"from": deployer})

    assert df_rewards.claimable(a1, OCEAN.address) == 50

    with brownie.reverts("Not enough rewards"):
        # Cannot claim what you don't have
        df_strategy.claimAndStake(
            OCEAN,
            100,
            veOCEAN,
            {"from": bob},
        )

    # veBalBefore = veOCEAN.balanceOf(deployer)
    df_strategy.claimAndStake(
        OCEAN,
        50,
        veOCEAN,
        {"from": bob},
    )

    assert df_rewards.claimable(a1, OCEAN.address) == 0


@enforce_types
def _deploy_token(account):
    return B.Simpletoken.deploy("TOK", "TOK", 18, to_wei(100.0), {"from": account})


@enforce_types
def setup_function():
    networkutil.connect_dev()
    global accounts, a1, a2, a3
    accounts = brownie.network.accounts
    a1, a2, a3 = accounts[1].address, accounts[2].address, accounts[3].address


@enforce_types
def teardown_function():
    networkutil.disconnect()
