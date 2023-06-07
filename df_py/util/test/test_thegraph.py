from pprint import pprint

import brownie
from enforce_typing import enforce_types

from df_py.util import networkutil, oceantestutil, oceanutil
from df_py.util.graphutil import submitQuery

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
