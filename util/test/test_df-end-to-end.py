import brownie
from enforce_typing import enforce_types
from pprint import pprint
import pytest

from util import calcrewards, query
from util.blockrange import BlockRange
from util.oceanutil import OCEAN_address, recordDeployedContracts
from util.test import conftest

accounts = brownie.network.accounts
chain = brownie.network.chain

@enforce_types
def test_main(ADDRESS_FILE, SUBGRAPH_URL):
    recordDeployedContracts(ADDRESS_FILE, "development")
    conftest.fillAccountsWithOCEAN()
    
    conftest.randomDeployTokensAndPoolsThenConsume(num_pools=2)
    
    st, fin, n = 1, len(chain), 5
    rng = BlockRange(st, fin, n)
    OCEAN_avail = 10000.0

    (stakes, poolvols) = query.query(rng, SUBGRAPH_URL)
    rates = {"ocean": 0.5, "h2o": 1.618}

    rewards = calcrewards.calcRewards(stakes, poolvols, rates, OCEAN_avail)
    sum_ = sum(rewards.values())
    assert sum_ == pytest.approx(OCEAN_avail, 0.01), sum_

