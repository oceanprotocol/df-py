from typing import Any

import brownie
from brownie.network import accounts
import pytest
from enforce_typing import enforce_types
from ocean_lib.web3_internal.utils import connect_to_network

from util import networkutil, oceanutil, oceantestutil
from util.random_addresses import get_random_addresses
from util.constants import BROWNIE_PROJECT as B


@enforce_types
def test_allocate_gas(OCEAN, df_rewards):
    one = _batch_allocate(1, OCEAN, df_rewards)
    two = _batch_allocate(2, OCEAN, df_rewards)
    nine = _batch_allocate(9, OCEAN, df_rewards)
    ten = _batch_allocate(10, OCEAN, df_rewards)

    per_iteration1 = two.gas_used - one.gas_used
    per_iteration2 = ten.gas_used - nine.gas_used

    # each iteration uses the same amount of gas
    assert abs(per_iteration2 - per_iteration1) < 50

    # 23167 is the estimated gas for each iteration
    assert abs(per_iteration1 - 23167) < 100

    # mainnet gas limit
    assert per_iteration1 * 1250 < 30_000_000


@enforce_types
def test_1250_addresses(OCEAN, df_rewards):
    big_batch = _batch_allocate(1250, OCEAN, df_rewards)

    # should be able to allocate 1250 addresses using less than 30,000,000 gas
    assert big_batch.gas_used < 30_000_000


@enforce_types
def _batch_allocate(number: int, OCEAN, df_rewards) -> str:
    addresses, rewards = _prep_batch_allocate(number, OCEAN, df_rewards)
    tx = df_rewards.allocate(addresses, rewards, OCEAN.address, {"from": accounts[0]})
    return tx


@enforce_types
def _prep_batch_allocate(number: int, OCEAN, df_rewards) -> Any:
    addresses = get_random_addresses(number)
    rewards = [1] * number
    OCEAN.approve(df_rewards.address, sum(rewards), {"from": accounts[0]})
    return addresses, rewards
