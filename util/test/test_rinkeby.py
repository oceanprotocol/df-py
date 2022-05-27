import brownie
from enforce_typing import enforce_types
from pprint import pprint
import pytest

from util import networkutil, oceanutil, oceantestutil
from util.graphutil import submitQuery
    

@enforce_types
def test_query_approvedTokens(accounts):
    print("hello")
    
    OCEAN = oceanutil.OCEANtoken()

    oceantestutil.randomDeployPool(accounts[0], OCEAN)

    query = "{ opcs{approvedTokens} }"
    result = submitQuery(query, chainID)

    pprint(result)


@enforce_types 
def accounts():
    chainID = networkutil.networkToChainId("rinkeby")
    networkutil.connect(chainID)
    
    address_file = networkutil.chainIdToAddressFile(chainID)
    oceanutil.recordDeployedContracts(address_file)
    oceantestutil.fillAccountsWithOCEAN()


@enforce_types
def teardown_module():
    networkutil.disconnect()
    
    
