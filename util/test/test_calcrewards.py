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
    end_block = len(brownie.network.chain)
    num_samples = 5
    random_seed = 3
    block_range = BlockRange(start_block, end_block, num_samples, random_seed)
    
    OCEAN_available = 10000.0
    rewards:dict = calcrewards.calcRewards(
        OCEAN_available, block_range, SUBGRAPH_URL)
    
    sum_rewards:float = sum(rewards.values())
    assert sum_rewards == pytest.approx(OCEAN_available, 0.01), sum_rewards

def test_getStake(ADDRESS_FILE, SUBGRAPH_URL):
    recordDeployedContracts(ADDRESS_FILE, "development")
    conftest.fillAccountsWithOCEAN()
    conftest.randomDeployTokensAndPoolsThenConsume(num_pools=1)
    
    start_block = 1
    end_block = 500 #HACK len(brownie.network.chain)
    num_samples = end_block - start_block + 1 #use every block
    block_range = BlockRange(start_block, end_block, num_samples)

    LPs = calcrewards.getLPs(block_range, SUBGRAPH_URL)
    pools = calcrewards.getPools(SUBGRAPH_URL)
    S = calcrewards.getStake(LPs, pools, block_range, SUBGRAPH_URL)

    assert S.amax() > 0.0
    
def test_getConsumeVolumes(ADDRESS_FILE, SUBGRAPH_URL):
    recordDeployedContracts(ADDRESS_FILE, "development")
    conftest.fillAccountsWithOCEAN()
    conftest.randomDeployTokensAndPoolsThenConsume(num_pools=1)
    st_block = 1
    end_block = len(brownie.network.chain)
    
    volumes = calcrewards.getConsumeVolumes(st_block, end_block, SUBGRAPH_URL)

    assert sum(volumes.values()) > 0.0
