import brownie
from enforce_typing import enforce_types
from pprint import pprint
import pytest

from util import calcrewards 
from util.blockrange import BlockRange
from util.oceanutil import recordDeployedContracts
from util.test import conftest

accounts = brownie.network.accounts

@enforce_types
def test_main(ADDRESS_FILE, SUBGRAPH_URL):
    recordDeployedContracts(ADDRESS_FILE, "development")
    conftest.fillAccountsWithOCEAN()
    conftest.randomDeployTokensAndPoolsThenConsume(num_pools=2)

    start_block = 0
    end_block = len(brownie.network.chain) - 3
    num_samples = 5
    random_seed = 3
    block_range = BlockRange(start_block, end_block, num_samples, random_seed)
    
    OCEAN_available = 10000.0
    rewards:dict = calcrewards.calcRewards(
        OCEAN_available, block_range, SUBGRAPH_URL)
    
    sum_rewards:float = sum(rewards.values())
    assert sum_rewards == pytest.approx(OCEAN_available, 0.01), sum_rewards

def test_getConsumeVolumes(ADDRESS_FILE, SUBGRAPH_URL):
    recordDeployedContracts(ADDRESS_FILE, "development")
    conftest.fillAccountsWithOCEAN()
    
    conftest.randomDeployTokensAndPoolsThenConsume(num_pools=1)
    end_block = len(brownie.network.chain)
    
    volumes = calcrewards.getConsumeVolumes(0, end_block, SUBGRAPH_URL)

    assert sum(volumes.values()) > 0.0
