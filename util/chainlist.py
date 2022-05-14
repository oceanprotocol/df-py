import ast
from enforce_typing import enforce_types
import re
import requests
from typing import Dict


@enforce_types
def chainIdToSubgraphUri(chainID: int) -> str:
    """Returns the subgraph URI for a given chainID"""
    if chainID == 0:
        return "http://127.0.0.1:9000" #ganache / barge
    else:
        raise NotImplementedError()


CHAINID_TO_NETWORK = None # dict of [chainID_int] : network_str
NETWORK_TO_CHAINID = None # dict of [network_str] : chainID_int

    
@enforce_types
def chainIdToNetwork(chainID: int) -> str:
    """Returns the network name for a given chainID"""
    #corner case
    if chainID == 0:
        return "development"

    #main case
    global CHAINID_TO_NETWORK
    if CHAINID_TO_NETWORK is None:
        _cacheDataFromChainlist()
    return CHAINID_TO_NETWORK[chainID]


def networkToChainId(network:str) -> int:
    """Returns the chainID for a given network name"""
    #corner case
    if network == "development":
        return 0
    
    #main case
    global NETWORK_TO_CHAINID
    if NETWORK_TO_CHAINID is None:
        _cacheDataFromChainlist()
    return NETWORK_TO_CHAINID[network]


def _cacheDataFromChainlist():
    """
    @description
      chainlist.org is a site that gives full info about each EVM chain.
      Its core data is found at the github url given below. 
      This function grabs that core data and stores it as a global.
    """
    global CHAINID_TO_NETWORK, NETWORK_TO_CHAINID
    if CHAINID_TO_NETWORK is not None:
        assert NETWORK_TO_CHAINID is not None, "should set both globals at once"
        return

    url = "https://raw.githubusercontent.com/DefiLlama/chainlist/main/constants/chainIds.js"
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

    CHAINID_TO_NETWORK = ast.literal_eval(text)
    NETWORK_TO_CHAINID = {network: chainID
                          for chainID, network in CHAINID_TO_NETWORK.items()}
    

