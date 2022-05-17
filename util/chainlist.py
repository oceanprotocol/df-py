import ast
from enforce_typing import enforce_types
import os
import re
import requests
from typing import Dict

_BARGE_ADDRESS_FILE = "~/.ocean/ocean-contracts/artifacts/address.json"
_BARGE_SUBGRAPH_URI = "http://127.0.0.1:9000/subgraphs/name/oceanprotocol/ocean-subgraph"

_CHAINID_TO_NETWORK = None # dict of [chainID_int] : network_str
_NETWORK_TO_CHAINID = None # dict of [network_str] : chainID_int
_CHAINIDS_JS_URL = "https://raw.githubusercontent.com/DefiLlama/chainlist/main/constants/chainIds.js"


@enforce_types
def chainIdToAddressFile(chainID: int) -> str:
    """Returns the address file for a given chainID"""
    if chainID == 0:
        return os.path.expanduser(_BARGE_ADDRESS_FILE)
    else:
        raise NotImplementedError()


@enforce_types
def chainIdToSubgraphUri(chainID: int) -> str:
    """Returns the subgraph URI for a given chainID"""
    if chainID == 0:
        return _BARGE_SUBGRAPH_URI
    else:
        raise NotImplementedError()


@enforce_types
def chainIdToNetwork(chainID: int) -> str:
    """Returns the network name for a given chainID"""
    #corner case
    if chainID == 0:
        return "development"

    #main case
    global _CHAINID_TO_NETWORK
    if _CHAINID_TO_NETWORK is None:
        _cacheDataFromChainlist()
    return _CHAINID_TO_NETWORK[chainID]


def networkToChainId(network:str) -> int:
    """Returns the chainID for a given network name"""
    #corner case
    if network == "development":
        return 0

    #main case
    global _NETWORK_TO_CHAINID
    if _NETWORK_TO_CHAINID is None:
        _cacheDataFromChainlist()
    return _NETWORK_TO_CHAINID[network]


def _cacheDataFromChainlist():
    """
    @description
      chainlist.org is a site that gives full info about each EVM chain.
      Its core data is found at the github url given below.
      This function grabs that core data and stores it as a global.
    """
    global _CHAINID_TO_NETWORK, _NETWORK_TO_CHAINID
    if _CHAINID_TO_NETWORK is not None:
        assert _NETWORK_TO_CHAINID is not None, "should set both globals at once"
        return

    url = _CHAINIDS_JS_URL
    resp = requests.get(url)

    text = resp.text
    #text looks like:
    #const chainIds = {
    # 0: "kardia",
    # 1: "ethereum",
    # ...

    text = text.replace("\n","") #remove whitespace
    text = re.sub(".*{", "{", text) #remove all before the "{"
    text = re.sub(",}.*", "}", text) #remove all after the "}"

    _CHAINID_TO_NETWORK = ast.literal_eval(text)

    dev_chains = {
        3: 'ropsten',
        4: 'rinkeby'
    }

    #inject eth development chains
    _CHAINID_TO_NETWORK = {**_CHAINID_TO_NETWORK, **dev_chains}

    _NETWORK_TO_CHAINID = {network: chainID
                           for chainID, network in _CHAINID_TO_NETWORK.items()}


