from enforce_typing import enforce_types

from df_py.web3util.networkutil import (
    chain_id_to_network,
    chain_id_to_subgraph_uri,
    network_to_chain_id,
)

CHAINID = network_to_chain_id("goerli")


@enforce_types
def test_chain_id_to_network():
    network_str = chain_id_to_network(CHAINID)
    assert network_str == "goerli"


@enforce_types
def test_chain_id_to_subgraph_uri():
    uri = chain_id_to_subgraph_uri(CHAINID)
    assert "subgraph.goerli.oceanprotocol.com" in uri
