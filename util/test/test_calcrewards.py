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
    rewards:dict = calrewards.calcRewards(
        OCEAN_available, block_range, SUBGRAPH_URL)
    
    sum_rewards:float = sum(rewards.values())
    assert sum_rewards == pytest.approx(OCEAN_available, 0.01), sum_rewards

def test_getConsumeVolumeAtDT(ADDRESS_FILE, SUBGRAPH_URL):
    recordDeployedContracts(ADDRESS_FILE, "development")
    start_block = len(brownie.network.chain) + 1
    
    #deploy DT & pool, buy DTs, consume 3 times
    (DT, pool) = conftest.deployPool(
        init_OCEAN_stake=100.0, DT_OCEAN_rate=1.0, DT_cap=1000.0,
        from_account=accounts[0])
    conftest.buyDT(
        pool, DT, DT_buy_amt=3.0, max_OCEAN=1000.0, from_account=accounts[0])
    for i in range(3):
        conftest.consumeDT(DT, accounts[0], accounts[0])
    
    #query for consume volume on just new blocks
    end_block = len(brownie.network.chain)
    num_samples = 10000
    block_range = BlockRange(start_block, end_block, num_samples)

    (vol, num_consumes, lastPriceValues) = calcrewards.getConsumeVolumeAtDT(
        DT.address, block_range, SUBGRAPH_URL)

    #results of call should just have info for the new pool
    assert num_consumes == 3
    assert len(lastPriceValues) == 3
    assert len(set(lastPriceValues)) == 1, "all lastPriceValues should be same"
    assert vol == num_consumes * lastPriceValues[0]
