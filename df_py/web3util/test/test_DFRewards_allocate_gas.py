from typing import Any

import pytest
from enforce_typing import enforce_types

from df_py.web3util.contract_base import ContractBase
from df_py.web3util.networkutil import DEV_CHAINID
from df_py.web3util.oceanutil import OCEAN_token
from df_py.web3util.random_addresses import get_random_addresses


# TODO: fix this test pylint: disable=fixme
@pytest.mark.skip("Skip after fixing and removing brownie")
@enforce_types
def test_1250_addresses(w3, account0):
    big_batch = _batch_allocate(w3, account0, 1250)

    # should be able to allocate 1250 addresses using less than 30,000,000 gas
    assert big_batch.gas_used < 30_000_000


# TODO: fix this test pylint: disable=fixme
@pytest.mark.skip("Skip after fixing and removing brownie")
@enforce_types
def test_insufficient_gas_reverts(w3, account0):
    addresses, rewards, token_addr, df_rewards = _prep_batch_allocate(
        w3, account0, 1250
    )
    with pytest.raises(Exception) as e_info:
        df_rewards.allocate(
            addresses, rewards, token_addr, {"from": account0, "gas_limit": 100000}
        )

    error_str = str(e_info.value)
    assert "out of gas" in error_str or "intrinsic gas too low" in error_str


@enforce_types
def _batch_allocate(w3, account0, n_accounts: int) -> str:
    addresses, rewards, token_addr, df_rewards = _prep_batch_allocate(
        w3, account0, n_accounts
    )
    tx = df_rewards.allocate(addresses, rewards, token_addr, {"from": account0})
    return tx


@enforce_types
def _prep_batch_allocate(w3, account0, n_accounts: int) -> Any:
    """
    @description
      Create 'n_accounts' random accounts, give each an OCEAN allowance.
      To help testing of df_rewards

    @return
      addresses -- list[address_str]
      rewards -- [1, 1, ..., n_accounts-1] -- reward in OCEAN per account
      OCEAN_address - str
      df_rewards -- DFRewards contract, controlled by account0.
        Account0 approves it to spend sum(rewards)
    """
    OCEAN = OCEAN_token(DEV_CHAINID)
    df_rewards = ContractBase(w3, "DFRewards", constructor_args=[])
    addresses = get_random_addresses(n_accounts)
    rewards = [1 for account_i in range(n_accounts)]
    OCEAN.approve(df_rewards, sum(rewards), {"from": account0})
    return addresses, rewards, OCEAN.address, df_rewards
