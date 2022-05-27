from enforce_typing import enforce_types
import pytest

from util import networkutil


@enforce_types
def test_chainIdToSubgraphUri():
    assert networkutil.chainIdToSubgraphUri(0)[:21] == "http://127.0.0.1:9000"

    for chainID in [1, 137]:
        with pytest.raises(NotImplementedError):
            networkutil.chainIdToSubgraphUri(chainID)


@enforce_types
def test_chainIdToNetwork():
    assert networkutil.chainIdToNetwork(8996) == "development"
    assert networkutil.chainIdToNetwork(1) == "mainnet"
    assert networkutil.chainIdToNetwork(137) == "Polygon Mainnet"


@enforce_types
def test_networkToChainId():
    assert networkutil.networkToChainId("development") == 8996
    assert networkutil.networkToChainId("mainnet") == 1
    assert networkutil.networkToChainId("Polygon Mainnet") == 137
