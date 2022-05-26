from enforce_typing import enforce_types
import pytest

from util import chainlist


@enforce_types
def test_chainIdToSubgraphUri():
    assert chainlist.chainIdToSubgraphUri(0)[:21] == "http://127.0.0.1:9000"

    for chainID in [1, 137]:
        with pytest.raises(NotImplementedError):
            chainlist.chainIdToSubgraphUri(chainID)


@enforce_types
def test_chainIdToNetwork():
    assert chainlist.chainIdToNetwork(0) == "development"
    assert chainlist.chainIdToNetwork(1) == "ethereum"
    assert chainlist.chainIdToNetwork(137) == "polygon"


@enforce_types
def test_networkToChainId():
    assert chainlist.networkToChainId("development") == 0
    assert chainlist.networkToChainId("ethereum") == 1
    assert chainlist.networkToChainId("polygon") == 137
