import ast
from enforce_typing import enforce_types
import re
import requests
from typing import Dict

CHAINID_TO_NETWORK = None # dict of [chainID_int] : network_str
NETWORK_TO_CHAINID = None # dict of [network_str] : chainID_int


@enforce_types
def chainIdToNetwork_forBrownie(chainID: int) -> str:
    """
    @description
      Maps chainID to network, but ensures network name is brownie-friendly.

      Examples:
        0: "development"
        137: "polygon"

    @arguments
      chainID -- int -- e.g. 137

    @return
      network -- str -- e.g. "polygon"
    """
    #special cases
    if chainID == 0:
        return "development"

    #default case
    else:
        return chainIdToNetwork(chainID)
    
@enforce_types
def chainIdToNetwork(chainID: int) -> str:
    """
    @description
      Directly uses chainlist.org info to map chainID to network.

      Examples:
        0: "kardia"
        137: "polygon"

    @arguments
      chainID -- int 

    @return
      network -- str
    """
    global CHAINID_TO_NETWORK
    if CHAINID_TO_NETWORK is None:
        _cacheDataFromChainlist()
    return CHAINID_TO_NETWORK[chainID]


def networkToChainId(network:str) -> int:
    """
    @description
      Directly uses chainlist.org info to map chainID to network.
    @arguments
      network -- str -- e.g. "polygon"
    @return
      chainID -- int -- e.g. 137
    """
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
    

