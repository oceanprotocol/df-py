from enforce_typing import enforce_types
from pprint import pprint

from util import oceanutil
from util.graphutil import submitQuery
from util.test import conftest

CHAINID = 0

@enforce_types
def test_thegraph_approvedTokens(ADDRESS_FILE, accounts):
    oceanutil.recordDeployedContracts(ADDRESS_FILE, CHAINID)
    OCEAN = oceanutil.OCEANtoken()

    conftest.randomDeployPool(accounts[0])

    query = "{ opcs{approvedTokens} }"
    result = submitQuery(query, CHAINID)

    pprint(result)


@enforce_types
def test_thegraph_orders(ADDRESS_FILE):
    oceanutil.recordDeployedContracts(ADDRESS_FILE, CHAINID)
    OCEAN = oceanutil.OCEANtoken()

    (_, DT, _) = conftest.randomDeployTokensAndPoolsThenConsume(num_pools=1)[0]

    query = """
        {
          orders(where: {block_gte:0, block_lte:1000, datatoken:"%s"}, 
                 skip:0, first:5) {
            id,
            datatoken {
              id
            }
            lastPriceToken,
            lastPriceValue
            estimatedUSDValue,
            block
          }
        }
        """ % (
        DT.address
    )
    result = submitQuery(query, CHAINID)
    pprint(result)


@enforce_types
def test_thegraph_poolShares(ADDRESS_FILE):
    oceanutil.recordDeployedContracts(ADDRESS_FILE, CHAINID)
    OCEAN = oceanutil.OCEANtoken()

    tups = conftest.randomDeployTokensAndPoolsThenConsume(num_pools=1)
    (_, DT, pool) = tups[0]

    skip = 0
    INC = 1000
    block = 0
    pool_addr = pool.address

    # poolShares(skip:%s, first:%s, block:{number:%s}, where: {pool_in:"%s"}) {
    query = """
        {
          poolShares(skip:%s, first:%s) {
            pool {
              id,
              totalShares
            }
            shares,
            user {
              id
            }
          }
        }
        """ % (
        skip,
        INC,
    )

    result = submitQuery(query, CHAINID)
    pprint(result)
