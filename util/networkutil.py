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

CHAIN_ADDRS = {
    8996: "0xdev",
    1: "0xeth",
    3: "0xropsten",
    4: "0xrinkeby",
    56: "0xbnb",
    137: "0xpolygon",
    246: "0xenergyweb",
    1285: "0xmoonriver",
    1287: "0xmoonbase",
    80001: "0xmumbai",
}


WRAPPED_TOKEN_SYMBOLS = {
    "0xdev": "OCEAN",
    "0xeth": "ETH",
    "0xropsten": "ETH",
    "0xrinkeby": "ETH",
    "0xbnb": "MATIC",
    "0xpolygon": "BNB",
    "0xenergyweb": "EWT",
    "0xmoonriver": "MOON",
    "0xmoonbase": "MOON",
    "0xmumbai": "MATIC",
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
