from enforce_typing import enforce_types

from util import chainlist


@enforce_types
def test_cacheData():
    chainlist._cacheDataFromChainlist()
    assert chainlist.CHAINID_TO_NETWORK[137] == "polygon"
    assert chainlist.NETWORK_TO_CHAINID["polygon"] == 137


@enforce_types
def test_chainIdToNetwork():
    assert chainlist.chainIdToNetwork(137) == "polygon"


@enforce_types
def test_networkToChainId():
    assert chainlist.networkToChainId("polygon") == 137
