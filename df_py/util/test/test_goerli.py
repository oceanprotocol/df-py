from enforce_typing import enforce_types

from df_py.util import networkutil

CHAINID = networkutil.network_to_chain_id("goerli")


@enforce_types
def test_chain_id_to_network():
    network_str = networkutil.chain_id_to_network(CHAINID)
    assert network_str == "goerli"


@enforce_types
def test_chain_id_to_subgraph_uri():
    uri = networkutil.chain_id_to_subgraph_uri(CHAINID)
    assert "subgraph.goerli.oceanprotocol.com" in uri
