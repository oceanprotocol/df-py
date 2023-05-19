import time

import brownie
from enforce_typing import enforce_types
import pytest

from util import dispense, networkutil, oceanutil
from util.base18 import from_wei
from util.constants import BROWNIE_PROJECT as B
from util import oceantestutil

chain, accounts, a1, a2, a3 = None, None, None, None, None


@enforce_types
def test_small_batch():
    OCEAN = oceanutil.OCEANtoken()
    df_rewards = B.DFRewards.deploy({"from": accounts[0]})
    df_strategy = B.DFStrategyV1.deploy(df_rewards.address, {"from": accounts[0]})

    rewards_at_chain = {a1: 0.1, a2: 0.2, a3: 0.3}
    dispense.dispense(
        rewards_at_chain,
        dfrewards_addr=df_rewards.address,
        token_addr=OCEAN.address,
        from_account=accounts[0],
    )

    # a1 claims for itself
    bal_before = from_wei(OCEAN.balanceOf(a1))
    df_strategy.claim([OCEAN.address], {"from": accounts[1]})
    _assertBalanceApprox(OCEAN, a1, bal_before + 0.1, tries=10)

    # a9 claims on behalf of a1
    bal_before = from_wei(OCEAN.balanceOf(a3))
    df_rewards.claimFor(a3, OCEAN.address, {"from": accounts[9]})
    _assertBalanceApprox(OCEAN, a3, bal_before + 0.3, tries=10)


@enforce_types
def test_batching():
    OCEAN = oceanutil.OCEANtoken()
    df_rewards = B.DFRewards.deploy({"from": accounts[0]})

    batch_size = 3
    N = batch_size * 3 + 1  # enough accounts to ensure batching
    assert len(accounts) >= N

    rewards_at_chain = {accounts[i]: (i + 1.0) for i in range(N)}

    dispense.dispense(
        rewards_at_chain,
        dfrewards_addr=df_rewards.address,
        token_addr=OCEAN.address,
        from_account=accounts[0],
        batch_size=batch_size,
    )

    for i in range(N):
        assert df_rewards.claimable(accounts[i], OCEAN.address) > 0


@enforce_types
def test_batch_number():
    TOK = B.Simpletoken.deploy("TOK", "TOK", 18, 100e18, {"from": accounts[0]})

    df_rewards = B.DFRewards.deploy({"from": accounts[0]})
    batch_size = 3
    N = batch_size * 3 + 1  # enough accounts to ensure batching
    assert len(accounts) >= N

    rewards_at_chain = {accounts[i]: (i + 1.0) for i in range(N)}

    dispense.dispense(
        rewards_at_chain,
        dfrewards_addr=df_rewards.address,
        token_addr=TOK.address,
        from_account=accounts[0],
        batch_size=batch_size,
        batch_number=2,
    )

    assert df_rewards.claimable(accounts[batch_size - 1], TOK.address) == 0
    assert df_rewards.claimable(accounts[batch_size], TOK.address) > 0
    assert df_rewards.claimable(accounts[batch_size + 1], TOK.address) > 0
    assert df_rewards.claimable(accounts[batch_size + 2], TOK.address) > 0
    assert df_rewards.claimable(accounts[batch_size + 3], TOK.address) == 0


@enforce_types
def _assertBalanceApprox(token, address:str, target_bal:float, tries:int):
    """Test for a balance, but with retries so that ganache can catch up"""
    for i in range(tries):
        bal = from_wei(token.balanceOf(address))
        if bal == pytest.approx(target_bal):
            return
        chain.sleep(1)
        chain.mine(1)
        time.sleep(1)
    assert bal == pytest.approx(target_bal)

    
@enforce_types
def setup_function():
    networkutil.connectDev()
    global chain, accounts, a1, a2, a3
    chain = brownie.network.chain
    accounts = brownie.network.accounts
    a1, a2, a3 = [accounts[i].address for i in [1,2,3]]
    oceanutil.recordDevDeployedContracts()
    oceantestutil.fillAccountsWithOCEAN()


@enforce_types
def teardown_function():
    networkutil.disconnect()
