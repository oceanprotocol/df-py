from unittest.mock import patch

import brownie
import pytest
from enforce_typing import enforce_types

from df_py.util import dispense, networkutil, oceantestutil, oceanutil
from df_py.util.base18 import from_wei
from df_py.util.constants import BROWNIE_PROJECT as B

accounts, a1, a2, a3 = None, None, None, None


@enforce_types
def test_small_batch():
    OCEAN = oceanutil.OCEAN_token()
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
    bal_after = from_wei(OCEAN.balanceOf(a1))
    assert (bal_after - bal_before) == pytest.approx(0.1)

    # a9 claims on behalf of a1
    bal_before = from_wei(OCEAN.balanceOf(a3))
    df_rewards.claimFor(a3, OCEAN.address, {"from": accounts[9]})
    bal_after = from_wei(OCEAN.balanceOf(a3))
    assert (bal_after - bal_before) == pytest.approx(0.3)


@enforce_types
def test_batching():
    OCEAN = oceanutil.OCEAN_token()
    df_rewards = B.DFRewards.deploy({"from": accounts[0]})

    batch_size = 3
    total_number = batch_size * 3 + 1  # enough accounts to ensure batching
    assert len(accounts) >= total_number

    rewards_at_chain = {accounts[i]: (i + 1.0) for i in range(total_number)}

    dispense.dispense(
        rewards_at_chain,
        dfrewards_addr=df_rewards.address,
        token_addr=OCEAN.address,
        from_account=accounts[0],
        batch_size=batch_size,
    )

    for i in range(total_number):
        assert df_rewards.claimable(accounts[i], OCEAN.address) > 0


@enforce_types
def test_batch_number():
    token = B.Simpletoken.deploy("TOK", "TOK", 18, 100e18, {"from": accounts[0]})

    df_rewards = B.DFRewards.deploy({"from": accounts[0]})
    batch_size = 3
    total_number = batch_size * 3 + 1  # enough accounts to ensure batching
    assert len(accounts) >= total_number

    rewards_at_chain = {accounts[i]: (i + 1.0) for i in range(total_number)}

    dispense.dispense(
        rewards_at_chain,
        dfrewards_addr=df_rewards.address,
        token_addr=token.address,
        from_account=accounts[0],
        batch_size=batch_size,
        batch_number=2,
    )

    assert df_rewards.claimable(accounts[batch_size - 1], token.address) == 0
    assert df_rewards.claimable(accounts[batch_size], token.address) > 0
    assert df_rewards.claimable(accounts[batch_size + 1], token.address) > 0
    assert df_rewards.claimable(accounts[batch_size + 2], token.address) > 0
    assert df_rewards.claimable(accounts[batch_size + 3], token.address) == 0


def test_dispense_passive():
    fee_distributor = oceanutil.FeeDistributor()
    OCEAN = oceanutil.OCEAN_token()
    with patch("df_py.util.dispense.chain_id_to_multisig_addr"):
        with patch("df_py.util.dispense.send_multisig_tx") as mock:
            dispense.dispense_passive(OCEAN, fee_distributor, 1)

    assert mock.call_count == 3


@enforce_types
def setup_function():
    networkutil.connect_dev()
    global accounts, a1, a2, a3
    accounts = brownie.network.accounts
    a1, a2, a3 = accounts[1].address, accounts[2].address, accounts[3].address
    address_file = networkutil.chain_id_to_address_file(networkutil.DEV_CHAINID)
    oceanutil.record_deployed_contracts(address_file)
    oceantestutil.fill_accounts_with_OCEAN()


@enforce_types
def teardown_function():
    networkutil.disconnect()
