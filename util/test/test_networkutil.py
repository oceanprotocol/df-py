from enforce_typing import enforce_types

from util import networkutil


@enforce_types
def test_chainIdToSubgraphUri():
    for chainID, network_str in networkutil._CHAINID_TO_NETWORK.items():
        uri = networkutil.chainIdToSubgraphUri(chainID)
        if chainID == networkutil.DEV_CHAINID:
            assert uri[:21] == "http://127.0.0.1:9000"
        else:
            assert network_str in uri


@enforce_types
def test_chainIdToNetwork():
    assert networkutil.chainIdToNetwork(8996) == "development"
    assert networkutil.chainIdToNetwork(1) == "mainnet"
    assert networkutil.chainIdToNetwork(137) == "polygon"


@enforce_types
def test_networkToChainId():
    assert networkutil.networkToChainId("development") == 8996
    assert networkutil.networkToChainId("mainnet") == 1
    assert networkutil.networkToChainId("polygon") == 137
