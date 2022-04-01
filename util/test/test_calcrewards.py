import brownie
from pprint import pprint
import pytest

from util.oceanutil import recordDeployedContracts
from util.calcrewards import calcRewards
from util.blockrange import BlockRange
from util.test import conftest

def test_main(ADDRESS_FILE, SUBGRAPH_URL):
    recordDeployedContracts(ADDRESS_FILE, "development")
    conftest.fillAccountsWithOCEAN()
    conftest.randomDeployAll(num_pools=2)

    start_block = 0
    end_block = len(brownie.network.chain) - 3
    num_samples = 5
    random_seed = 3
    block_range = BlockRange(start_block, end_block, num_samples, random_seed)
    
    OCEAN_available = 10000.0
    rewards = calcRewards(OCEAN_available, block_range, SUBGRAPH_URL)
    
    sum_rewards = sum(rewards.values())
    assert sum_rewards == pytest.approx(OCEAN_available, 0.01), sum_rewards
