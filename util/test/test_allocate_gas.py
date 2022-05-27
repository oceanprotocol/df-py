from typing import Any

import brownie
import pytest
from enforce_typing import enforce_types
from util.random_addresses import get_random_addresses
from util.oceanutil import recordDeployedContracts, OCEANtoken
from util.constants import BROWNIE_PROJECT as B

accounts = brownie.network.accounts
CHAINID = networkutil.DEV_CHAINID


@enforce_types
def _prep_batch_allocate(number: int) -> Any:
    OCEAN = OCEANtoken()
    df_rewards = B.DFRewards.deploy({"from": accounts[0]})
    addresses = get_random_addresses(number)
    rewards = [1 for i in range(number)]
    OCEAN.approve(df_rewards, sum(rewards), {"from": accounts[0]})
    return addresses, rewards, OCEAN.address, df_rewards


@enforce_types
def batch_allocate(number: int) -> str:
    addresses, rewards, token_addr, df_rewards = _prep_batch_allocate(number)
    tx = df_rewards.allocate(addresses, rewards, token_addr, {"from": accounts[0]})
    return tx


@enforce_types
def test_allocate_gas(ADDRESS_FILE):
    recordDeployedContracts(ADDRESS_FILE)

    one = batch_allocate(1)
    two = batch_allocate(2)
    nine = batch_allocate(9)
    ten = batch_allocate(10)

    per_iteration1 = two.gas_used - one.gas_used
    per_iteration2 = ten.gas_used - nine.gas_used

    assert (
        abs(per_iteration2 - per_iteration1) < 50
    )  # each iteration uses the same amount of gas
    assert (
        abs(per_iteration1 - 23167) < 100
    )  # 23167 is the estimated gas for each iteration
    assert per_iteration1 * 1250 < 30_000_000  # mainnet gas limit


def test_1250_addresses(ADDRESS_FILE):
    recordDeployedContracts(ADDRESS_FILE)

    big_batch = batch_allocate(1250)
    assert (
        big_batch.gas_used < 30_000_000
    )  # should be able to allocate 1250 addresses using less than 30,000,000 gas.


def test_insufficient_gas_reverts(ADDRESS_FILE):
    recordDeployedContracts(ADDRESS_FILE)
    addresses, rewards, token_addr, df_rewards = _prep_batch_allocate(1250)
    with pytest.raises(Exception) as e_info:
        df_rewards.allocate(
            addresses, rewards, token_addr, {"from": accounts[0], "gas_limit": 100000}
        )
    assert str(e_info.value) == "base fee exceeds gas limit"
