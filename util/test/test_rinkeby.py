import brownie
from enforce_typing import enforce_types
from pprint import pprint

from util import networkutil, oceanutil
from util.graphutil import submitQuery
from util import oceantestutil

network = brownie.network
    

@enforce_types
def test_query_approvedTokens(accounts):
    print("hello")
    
    CHAINID = 4 #rinkeby
    ADDRESS_FILE = networkutil.chainIdToAddressFile(CHAINID)
    
    # oceanutil.recordDeployedContracts(ADDRESS_FILE)
    # oceantestutil.fillAccountsWithOCEAN()

    # OCEAN = oceanutil.OCEANtoken()

    # oceantestutil.randomDeployPool(accounts[0], OCEAN)

    # query = "{ opcs{approvedTokens} }"
    # result = submitQuery(query, CHAINID)

    # pprint(result)

def setup_module():
    #development -> rinkeby
    if network.is_connected():
        network.disconnect()
    network.connect("rinkeby")

def teardown_module():
    #rinkeby -> development
    network.disconnect()
    network.connect("development")
    
    
