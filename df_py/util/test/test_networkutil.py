from enforce_typing import enforce_types

from df_py.util import networkutil


@enforce_types
def test_chain_id_to_subgraph_uri():
    for chainID, network_str in networkutil._CHAINID_TO_NETWORK.items():
        uri = networkutil.chain_id_to_subgraph_uri(chainID)
        if chainID == networkutil.DEV_CHAINID:
            assert uri[:21] == "http://127.0.0.1:9000"
        else:
            assert network_str in uri


@enforce_types
def test_chain_id_to_network():
    assert networkutil.chain_id_to_network(8996) == "development"
    assert networkutil.chain_id_to_network(1) == "mainnet"
    assert networkutil.chain_id_to_network(137) == "polygon"


@enforce_types
def test_network_to_chain_id():
    assert networkutil.network_to_chain_id("development") == 8996
    assert networkutil.network_to_chain_id("mainnet") == 1
    assert networkutil.network_to_chain_id("polygon") == 137
