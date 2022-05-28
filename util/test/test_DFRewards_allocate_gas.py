from typing import Any

import brownie
import pytest
from enforce_typing import enforce_types

from util import networkutil, oceanutil, oceantestutil
from util.random_addresses import get_random_addresses
from util.constants import BROWNIE_PROJECT as B


@enforce_types
def test_allocate_gas():
    one = _batch_allocate(1)
    two = _batch_allocate(2)
    nine = _batch_allocate(9)
    ten = _batch_allocate(10)

    per_iteration1 = two.gas_used - one.gas_used
    per_iteration2 = ten.gas_used - nine.gas_used

    # each iteration uses the same amount of gas
    assert abs(per_iteration2 - per_iteration1) < 50

    # 23167 is the estimated gas for each iteration
    assert abs(per_iteration1 - 23167) < 100

    # mainnet gas limit
    assert per_iteration1 * 1250 < 30_000_000


@enforce_types
def test_1250_addresses():
    big_batch = _batch_allocate(1250)

    # should be able to allocate 1250 addresses using less than 30,000,000 gas
    assert big_batch.gas_used < 30_000_000


@enforce_types
def test_insufficient_gas_reverts():
    account0 = brownie.network.accounts[0]
    addresses, rewards, token_addr, df_rewards = _prep_batch_allocate(1250)
    with pytest.raises(Exception) as e_info:
        df_rewards.allocate(
            addresses, rewards, token_addr, {"from": account0, "gas_limit": 100000}
        )
    assert str(e_info.value) == "base fee exceeds gas limit"


@enforce_types
def _batch_allocate(number: int) -> str:
    account0 = brownie.network.accounts[0]
    addresses, rewards, token_addr, df_rewards = _prep_batch_allocate(number)
    tx = df_rewards.allocate(addresses, rewards, token_addr, {"from": account0})
    return tx


@enforce_types
def _prep_batch_allocate(number: int) -> Any:
    account0 = brownie.network.accounts[0]
    OCEAN = oceanutil.OCEANtoken()
    df_rewards = B.DFRewards.deploy({"from": account0})
    addresses = get_random_addresses(number)
    rewards = [1 for i in range(number)]
    OCEAN.approve(df_rewards, sum(rewards), {"from": account0})
    return addresses, rewards, OCEAN.address, df_rewards


@enforce_types
def setup_function():
    networkutil.connect(networkutil.DEV_CHAINID)
    oceanutil.recordDevDeployedContracts()
    oceantestutil.fillAccountsWithOCEAN()


@enforce_types
def teardown_function():
    networkutil.disconnect()
