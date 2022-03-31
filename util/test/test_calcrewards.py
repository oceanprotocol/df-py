#Draws from https://github.com/oceanprotocol/df-js/blob/main/script/index.js

import brownie
from pprint import pprint
import pytest

from util.oceanutil import recordDeployedContracts
from util.rewardsutil import BlockRange, calcRewards
from util.test import conftest

def test_1(ADDRESS_FILE, SUBGRAPH_URL):
    recordDeployedContracts(ADDRESS_FILE, "development")
    conftest.fillAccountsWithOCEAN()
    conftest.randomDeployAll(num_pools=2)

    start_block = 0
    end_block = len(brownie.network.chain) - 3
    block_interval = 10
    block_range = BlockRange(start_block, end_block, block_interval)
    
    OCEAN_available = 10000.0
    rewards = calcRewards(OCEAN_available, block_range, SUBGRAPH_URL)
    
    sum_rewards = sum(rewards.values())
    assert sum_rewards == pytest.approx(OCEAN_available, 0.01), sum_rewards

    
