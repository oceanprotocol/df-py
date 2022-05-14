from enforce_typing import enforce_types
import pytest

from util import chainlist


@enforce_types
def test_chainIdToSubgraphUri():
    assert chainlist.chainIdToSubgraphUri(0) == "http://127.0.0.1:9000"
    
    for chainID in [1, 137]:
        with pytest.raises(NotImplementedError):
            chainlist.chainIdToSubgraphUri(chainID)


@enforce_types
def test_cacheData():
    chainlist._cacheDataFromChainlist()
    assert chainlist.CHAINID_TO_NETWORK[137] == "polygon"
    assert chainlist.NETWORK_TO_CHAINID["polygon"] == 137


@enforce_types
def test_chainIdToNetwork_forBrownie():
    assert chainlist.chainIdToNetwork_forBrownie(0) == "development"
    assert chainlist.chainIdToNetwork_forBrownie(137) == "polygon"

    
@enforce_types
def test_chainIdToNetwork():
    assert chainlist.chainIdToNetwork(0) == "kardia"
    assert chainlist.chainIdToNetwork(137) == "polygon"


@enforce_types
def test_networkToChainId():
    assert chainlist.networkToChainId("kardia") == 0
    assert chainlist.networkToChainId("polygon") == 137
