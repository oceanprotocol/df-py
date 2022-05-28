import brownie
from enforce_typing import enforce_types
from pprint import pprint
import pytest

from util import networkutil, oceanutil, oceantestutil
from util.graphutil import submitQuery

CHAINID = networkutil.networkToChainId("rinkeby")

@enforce_types
def test_chainIdToNetwork():
    network_str = networkutil.chainIdToNetwork(CHAINID)
    assert network_str == "rinkeby"
    
@enforce_types
def test_chainIdToSubgraphUri():
    uri = networkutil.chainIdToSubgraphUri(CHAINID)
    assert "subgraph.rinkeby.oceanprotocol.com" in uri
    
@enforce_types
def test_main():
    #setup_function
    networkutil.connect(CHAINID)
    address_file = networkutil.chainIdToAddressFile(CHAINID)
    oceanutil.recordDeployedContracts(address_file)

    #main
    assert brownie.network.chain.id == CHAINID
    
    query = "{ opcs{approvedTokens} }"
    result = submitQuery(query, CHAINID)
    
    OCEAN = oceanutil.OCEANtoken()
    assert OCEAN.symbol() == "OCEAN"

    #teardown_function
    networkutil.disconnect()

