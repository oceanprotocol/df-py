from enforce_typing import enforce_types

from df_py.web3util.networkutil import (
    _CHAINID_TO_NETWORK,
    chain_id_to_network,
    chain_id_to_subgraph_uri,
    DEV_CHAINID,
    network_to_chain_id,
)


@enforce_types
def test_chain_id_to_subgraph_uri():
    for chainID, network_str in _CHAINID_TO_NETWORK.items():
        uri = chain_id_to_subgraph_uri(chainID)
        if chainID == DEV_CHAINID:
            assert uri[:21] == "http://127.0.0.1:9000"
        else:
            assert network_str in uri


@enforce_types
def test_chain_id_to_network():
    assert chain_id_to_network(8996) == "development"
    assert chain_id_to_network(1) == "mainnet"
    assert chain_id_to_network(137) == "polygon"


@enforce_types
def test_network_to_chain_id():
    assert network_to_chain_id("development") == 8996
    assert network_to_chain_id("mainnet") == 1
    assert network_to_chain_id("polygon") == 137
