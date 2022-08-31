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
    query = "{ opcs{approvedTokens} }"
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
