import ast
import os
import re
from typing import Dict

import requests

from enforce_typing import enforce_types

_BARGE_ADDRESS_FILE = "~/.ocean/ocean-contracts/artifacts/address.json"
_BARGE_SUBGRAPH_URI = (
    "http://127.0.0.1:9000/subgraphs/name/oceanprotocol/ocean-subgraph"
)


#Chainid values are from from chainlist.org. Except we set chainid=0.
_CHAINID_TO_NETWORK = {
    0 : "development",
    1 : "ethereum",
    3 : "ropsten",
    4 : "rinkeby",
    56 : "bsc",
    137 : "polygon",
    246 : "ewc",
    1284 : "moonbeam",
    1285 : "moonriver"
    }
_NETWORK_TO_CHAINID = {
    network: chainID for chainID, network in _CHAINID_TO_NETWORK.items()
}


@enforce_types
def chainIdToAddressFile(chainID: int) -> str:
    """Returns the address file for a given chainID"""
    if chainID == 0:
        return os.path.expanduser(_BARGE_ADDRESS_FILE)

    raise NotImplementedError()


@enforce_types
def chainIdToSubgraphUri(chainID: int) -> str:
    """Returns the subgraph URI for a given chainID"""
    if chainID == 0:
        return _BARGE_SUBGRAPH_URI

    raise NotImplementedError()


@enforce_types
def chainIdToNetwork(chainID: int) -> str:
    """Returns the network name for a given chainID"""
    return _CHAINID_TO_NETWORK[chainID]


@enforce_types
def networkToChainId(network: str) -> int:
    """Returns the chainID for a given network name"""
    return _NETWORK_TO_CHAINID[network]
