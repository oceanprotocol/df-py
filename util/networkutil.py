import os

import brownie
from enforce_typing import enforce_types

from util.constants import CONTRACTS

_BARGE_ADDRESS_FILE = "~/.ocean/ocean-contracts/artifacts/address.json"

# Development chainid is from brownie, rest are from chainlist.org
# Chain values to fit Ocean subgraph urls as given in
# https://v3.docs.oceanprotocol.com/concepts/networks/
_CHAINID_TO_NETWORK = {
    8996: "development",  # ganache
    1: "mainnet",
    3: "ropsten",
    4: "rinkeby",
    56: "bsc",
    137: "polygon",
    246: "energyweb",
    1287: "moonbase",
    1285: "moonriver",
    80001: "mumbai",
}
_NETWORK_TO_CHAINID = {
    network: chainID for chainID, network in _CHAINID_TO_NETWORK.items()
}

DEV_CHAINID = _NETWORK_TO_CHAINID["development"]

WRAPPED_TOKEN_ADDRS = {
    1: "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
    3: "0xc778417e063141139fce010982780140aa0cd5ab",
    4: "0xc778417E063141139Fce010982780140Aa0cD5Ab",
    137: "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270",
    56: "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",
    # TODO Add more
}


WRAPPED_TOKEN_SYMBOLS = {
    WRAPPED_TOKEN_ADDRS[1]: "ETH",
    WRAPPED_TOKEN_ADDRS[3]: "ETH",
    WRAPPED_TOKEN_ADDRS[4]: "ETH",
    WRAPPED_TOKEN_ADDRS[137]: "MATIC",
    WRAPPED_TOKEN_ADDRS[56]: "BNB",
    # TODO Add more
}


@enforce_types
def chainIdToAddressFile(chainID: int) -> str:  # pylint: disable=unused-argument
    """Returns the address file for a given chainID"""
    return os.path.expanduser(_BARGE_ADDRESS_FILE)


@enforce_types
def chainIdToSubgraphUri(chainID: int) -> str:
    """Returns the subgraph URI for a given chainID"""
    sg = "/subgraphs/name/oceanprotocol/ocean-subgraph"
    if chainID == DEV_CHAINID:
        return "http://127.0.0.1:9000" + sg

    network_str = chainIdToNetwork(chainID)
    return f"https://v4.subgraph.{network_str}.oceanprotocol.com" + sg


@enforce_types
def chainIdToNetwork(chainID: int) -> str:
    """Returns the network name for a given chainID"""
    return _CHAINID_TO_NETWORK[chainID]


@enforce_types
def networkToChainId(network: str) -> int:
    """Returns the chainID for a given network name"""
    return _NETWORK_TO_CHAINID[network]


@enforce_types
def connect(chainID: int):
    network = brownie.network
    if network.is_connected():
        disconnect()  # call networkutil.disconnect(), *NOT* brownie directly
    network.connect(chainIdToNetwork(chainID))


@enforce_types
def disconnect():
    network = brownie.network
    if not network.is_connected():
        return

    chainID = network.chain.id
    if chainID in CONTRACTS:
        del CONTRACTS[chainID]

    try:
        network.disconnect()
    except:  # pylint: disable=bare-except
        # overcome brownie issue
        # https://github.com/eth-brownie/brownie/issues/1144
        pass
