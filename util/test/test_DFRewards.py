import time

import brownie
from enforce_typing import enforce_types
import pytest

from util.constants import BROWNIE_PROJECT as B
from util.base18 import to_wei
from util import networkutil, oceanutil

chain, accounts = None, None
acct0, acct1, acct2, acct3 = None, None, None, None
addr0, addr1, addr2, addr3 = None, None, None, None


@enforce_types
def test_basic():
    TOK = _deployTOK(acct0)
    df_rewards = B.DFRewards.deploy({"from": acct0})
    assert df_rewards.claimable(addr1, TOK.address) == 0


@enforce_types
def test_lostERC20():
    # Can recover when an account accidentally sends ERC20 to DFRewards.sol?
    # test_withdrawfunc.py handles this, so no work here
    pass


@enforce_types
def test_lostETH():
    # Can recover when an account accidentally sends ETH to DFRewards.sol?
    # test_withdrawfunc.py handles this, so no work here
    pass


@enforce_types
def test_TOK():
    TOK = _deployTOK(accounts[9])
    TOK.transfer(acct0.address, to_wei(100.0), {"from": accounts[9]})

    df_rewards = B.DFRewards.deploy({"from": acct0})
    df_strategy = B.DFStrategyV1.deploy(df_rewards.address, {"from": acct0})

    tos = [addr1, addr2, addr3]
    values = [10, 20, 30]
    TOK.approve(df_rewards, sum(values), {"from": acct0})
    df_rewards.allocate(tos, values, TOK.address, {"from": acct0})

    assert df_rewards.claimable(addr1, TOK.address) == 10
    assert df_rewards.claimable(addr2, TOK.address) == 20
    assert df_rewards.claimable(addr3, TOK.address) == 30

    # acct1 claims for itself
    assert TOK.balanceOf(addr1) == 0
    df_strategy.claim([TOK.address], {"from": acct1})
    _assertBalanceOf(TOK, addr1, 10, tries=10)

    # acct2 claims for itself too
    assert TOK.balanceOf(addr2) == 0
    df_strategy.claim([TOK.address], {"from": acct2})
    _assertBalanceOf(TOK, addr2, 20, tries=10)

    # acct9 claims for addr3
    assert TOK.balanceOf(addr3) == 0
    df_rewards.claimFor(addr3, TOK.address, {"from": accounts[9]})
    _assertBalanceOf(TOK, addr3, 30, tries=10)


@enforce_types
def test_OCEAN():
    oceanutil.recordDevDeployedContracts()
    oceanutil.mintOCEAN()
    OCEAN = oceanutil.OCEAN()
    assert OCEAN.balanceOf(acct0) >= 10

    df_rewards = B.DFRewards.deploy({"from": acct0})
    df_strategy = B.DFStrategyV1.deploy(df_rewards.address, {"from": acct0})

    OCEAN.approve(df_rewards, 10, {"from": acct0})
    df_rewards.allocate([addr1], [10], OCEAN.address, {"from": acct0})
    assert df_rewards.claimable(addr1, OCEAN.address) == 10

    bal_before = OCEAN.balanceOf(addr1)
    df_strategy.claim([OCEAN.address], {"from": acct1})
    _assertBalanceOf(OCEAN, addr1, bal_before + 10, tries=10)


@enforce_types
def test_multiple_TOK():
    TOK1 = _deployTOK(acct0)
    TOK2 = _deployTOK(acct0)

    df_rewards = B.DFRewards.deploy({"from": acct0})
    df_strategy = B.DFStrategyV1.deploy(df_rewards.address, {"from": acct0})

    tos = [addr1, addr2, addr3]
    values = [10, 20, 30]

    TOK1.approve(df_rewards, sum(values), {"from": acct0})
    TOK2.approve(df_rewards, sum(values) + 15, {"from": acct0})

    df_rewards.allocate(tos, values, TOK1.address, {"from": acct0})
    df_rewards.allocate(tos, [x + 5 for x in values], TOK2.address, {"from": acct0})

    TOK_addrs = [TOK1.address, TOK2.address]
    assert df_strategy.claimables(addr1, TOK_addrs) == [10, 15]
    assert df_strategy.claimables(addr2, TOK_addrs) == [20, 25]
    assert df_strategy.claimables(addr3, TOK_addrs) == [30, 35]

    # multiple claims

    # addr1 claims for itself
    assert TOK1.balanceOf(addr1) == 0
    assert TOK2.balanceOf(addr1) == 0
    df_strategy.claim([TOK1.address, TOK2.address], {"from": acct1})
    _assertBalanceOf(TOK1, addr1, 10, tries=10)
    _assertBalanceOf(TOK2, addr1, 15, tries=10)

    # addr2 claims for itself
    assert TOK1.balanceOf(addr2) == 0
    assert TOK2.balanceOf(addr2) == 0
    df_strategy.claim([TOK1.address, TOK2.address], {"from": acct2})
    _assertBalanceOf(TOK1, addr2, 20, tries=10)
    _assertBalanceOf(TOK2, addr2, 25, tries=10)

    # addr3 claims for itself
    assert TOK1.balanceOf(addr3) == 0
    assert TOK2.balanceOf(addr3) == 0
    df_strategy.claim([TOK1.address, TOK2.address], {"from": acct3})
    _assertBalanceOf(TOK1, addr3, 30, tries=10)
    _assertBalanceOf(TOK2, addr3, 35, tries=10)

    # addr1 can't claim extra
    assert TOK1.balanceOf(addr1) == 10
    assert TOK2.balanceOf(addr1) == 15
    df_strategy.claim([TOK1.address, TOK2.address], {"from": acct1})
    _assertBalanceOf(TOK1, addr1, 10, tries=10)
    _assertBalanceOf(TOK2, addr1, 15, tries=10)


@enforce_types
def test_bad_token():
    BADTOK = B.Badtoken.deploy("BAD", "BAD", 18, to_wei(10000.0), {"from": acct0})
    df_rewards = B.DFRewards.deploy({"from": acct0})

    tos = [addr1, addr2, addr3]
    values = [10, 20, 30]

    BADTOK.approve(df_rewards, sum(values), {"from": acct0})

    with pytest.raises(ValueError) as e:
        df_rewards.allocate(tos, values, BADTOK.address, {"from": acct0})
        assert "Not enough tokens" in str(e)


@enforce_types
def test_strategies():
    TOK = _deployTOK(acct0)

    df_rewards = B.DFRewards.deploy({"from": acct0})
    df_strategy = B.DummyStrategy.deploy(df_rewards.address, {"from": acct0})

    # allocate rewards
    tos = [addr1, addr2, addr3]
    values = [10, 20, 30]
    TOK.approve(df_rewards, sum(values), {"from": acct0})
    df_rewards.allocate(tos, values, TOK.address, {"from": acct0})

    assert TOK.balanceOf(df_strategy) == 0

    # tx origin must be addr1
    with pytest.raises(ValueError) as e:
        df_strategy.claim(TOK.address, addr1, {"from": acct2})
    assert "Caller doesn't match" in str(e)

    # non strategy addresses cannot claim
    with pytest.raises(ValueError) as e:
        df_strategy.claim(TOK.address, addr1, {"from": acct1})
    assert "Caller must be a strategy" in str(e)

    # add strategy
    df_rewards.addStrategy(df_strategy.address, {"from": acct0})
    assert df_rewards.isStrategy(df_strategy.address)
    assert df_rewards.live_strategies(0) == df_strategy.address

    # should claim since it's a strategy
    df_strategy.claim(TOK.address, addr1, {"from": acct1})

    # strategy balance increases
    assert TOK.balanceOf(df_strategy) == 10

    # should claim since it's a strategy
    df_strategy.claim(TOK.address, addr2, {"from": acct2})

    # strategy balance increases
    _assertBalanceOf(TOK, df_strategy.address, 30, tries=10)

    # retire strategy
    df_rewards.retireStrategy(df_strategy.address, {"from": acct0})
    assert not df_rewards.isStrategy(df_strategy.address)

    # addresses other than the owner cannot add new strategy
    with pytest.raises(ValueError) as e:
        df_rewards.addStrategy(df_strategy.address, {"from": acct3})
    assert "Ownable: caller is not the owner" in str(e)

    # add strategy
    df_rewards.addStrategy(df_strategy.address, {"from": acct0})
    assert df_rewards.isStrategy(df_strategy.address)
    assert df_rewards.live_strategies(0) == df_strategy.address

    # should claim since it's a strategy
    df_strategy.claim(TOK.address, addr3, {"from": acct3})

    # strategy balance increases
    _assertBalanceOf(TOK, df_strategy.address, 60, tries=10)


@enforce_types
def _test_claim_and_restake():
    oceanutil.recordDevDeployedContracts()
    oceanutil.mintOCEAN()
    OCEAN = oceanutil.OCEAN()
    deployer = acct0
    bob = acct1

    OCEAN.transfer(bob, 100, {"from": deployer})

    df_rewards = B.DFRewards.deploy({"from": deployer})
    df_strategy = B.DFStrategyV1.deploy(df_rewards.address, {"from": deployer})
    df_rewards.addStrategy(df_strategy.address)

    veOCEAN = B.veOcean.deploy(
        OCEAN.address, "veOCEAN", "veOCEAN", "0.1.0", {"from": deployer}
    )

    OCEAN.approve(veOCEAN.address, 100, {"from": bob})
    unlock_time = chain.time() + 14 * 86400
    veOCEAN.create_lock(100, unlock_time, {"from": bob})

    tos = [addr1]
    values = [50]
    OCEAN.approve(df_rewards, sum(values), {"from": deployer})
    df_rewards.allocate(tos, values, OCEAN.address, {"from": deployer})

    assert df_rewards.claimable(addr1, OCEAN.address) == 50

    with pytest.raises(ValueError) as e:
        # Cannot claim what you don't have
        df_strategy.claimAndStake(OCEAN, 100, veOCEAN, {"from": bob})
    assert "Not enough rewards" in str(e)

    df_strategy.claimAndStake(OCEAN, 50, veOCEAN, {"from": bob})

    assert df_rewards.claimable(addr1, OCEAN.address) == 0


@enforce_types
def _deployTOK(account):
    return B.Simpletoken.deploy("TOK", "TOK", 18, to_wei(100.0), {"from": account})


@enforce_types
def _assertBalanceOf(token, address: str, target_bal: int, tries: int):
    """Test for a balance, but with retries so that ganache can catch up"""
    for _ in range(tries):
        bal = token.balanceOf(address)
        if bal == target_bal:
            return
        chain.sleep(1)  # type: ignore[attr-defined]
        chain.mine(1)  # type: ignore[attr-defined]
        time.sleep(1)
    assert bal == target_bal


@enforce_types
def setup_module():
    networkutil.connectDev()
    global chain, accounts
    global acct0, acct1, acct2, acct3, addr0, addr1, addr2, addr3

    chain, accounts = brownie.chain, brownie.network.accounts
    acct0, acct1, acct2, acct3 = accounts[:4]
    addr0, addr1, addr2, addr3 = [a.address for a in accounts][:4]


@enforce_types
def teardown_module():
    networkutil.disconnect()
