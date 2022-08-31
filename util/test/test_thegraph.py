from pprint import pprint
from enforce_typing import enforce_types

import brownie

from util import networkutil, oceanutil
from util.graphutil import submitQuery
from util import oceantestutil

CHAINID = networkutil.DEV_CHAINID

accounts = None


@enforce_types
def test_approvedTokens():
    OCEAN = oceanutil.OCEANtoken()

    oceantestutil.randomDeployPool(accounts[0], OCEAN)

    query = "{ opcs{approvedTokens} }"
    result = submitQuery(query, CHAINID)

    pprint(result)


@enforce_types
def test_orders():
    OCEAN = oceanutil.OCEANtoken()

    (_, DT, _) = oceantestutil.randomDeployTokensAndPoolsThenConsume(
        num_pools=1, base_token=OCEAN
    )[0]

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
def setup_function():
    networkutil.connect(CHAINID)
    global accounts
    accounts = brownie.network.accounts
    oceanutil.recordDevDeployedContracts()
    oceantestutil.fillAccountsWithOCEAN()


@enforce_types
def teardown_function():
    networkutil.disconnect()
