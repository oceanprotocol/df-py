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
def test_poolShares():
    OCEAN = oceanutil.OCEANtoken()

    _ = oceantestutil.randomDeployTokensAndPoolsThenConsume(num_pools=1, base_token=OCEAN)
    # (_, DT, pool) = tups[0]

    skip = 0
    INC = 1000
    # block = 0
    # pool_addr = pool.address

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


@enforce_types
def setup_module():
    networkutil.connect(CHAINID)
    global accounts
    accounts = brownie.network.accounts
    address_file = networkutil.chainIdToAddressFile(CHAINID)
    oceanutil.recordDeployedContracts(address_file)
    oceantestutil.fillAccountsWithOCEAN()


@enforce_types
def teardown_module():
    networkutil.disconnect()
