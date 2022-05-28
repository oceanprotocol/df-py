import os

import brownie
from enforce_typing import enforce_types

from util.constants import CONTRACTS

_BARGE_ADDRESS_FILE = "~/.ocean/ocean-contracts/artifacts/address.json"
_BARGE_SUBGRAPH_URI = (
    "http://127.0.0.1:9000/subgraphs/name/oceanprotocol/ocean-subgraph"
)


# Chainid values & names are from brownie, where possible.
# https://eth-brownie.readthedocs.io/en/stable/network-management.html
# Otherwise, values & names are from networkutil.org.
_CHAINID_TO_NETWORK = {
    8996: "development",  # ganache
    1: "mainnet",  # eth mainnet
    3: "ropsten",
    4: "rinkeby",
    56: "Binance Smart Chain",
    137: "Polygon Mainnet",
    246: "Energy Web Chain",
    1284: "Moonbeam",
    1285: "Moonriver",
}
_NETWORK_TO_CHAINID = {
    network: chainID for chainID, network in _CHAINID_TO_NETWORK.items()
}

DEV_CHAINID = _NETWORK_TO_CHAINID["development"]


@enforce_types
def chainIdToAddressFile(chainID: int) -> str:
    """Returns the address file for a given chainID"""
    if chainID == DEV_CHAINID:
        return os.path.expanduser(_BARGE_ADDRESS_FILE)

    raise NotImplementedError()


@enforce_types
def chainIdToSubgraphUri(chainID: int) -> str:
    """Returns the subgraph URI for a given chainID"""
    if chainID == DEV_CHAINID:
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


@enforce_types
def connect(chainID: int):
    network = brownie.network
    if network.is_connected():
        network.disconnect()
    network.connect(chainIdToNetwork(chainID))


@enforce_types
def disconnect():
    network = brownie.network
    if not network.is_connected():
        return

    chainID = network.chain.id
    if chainID in CONTRACTS:
        del CONTRACTS[chainID]

    network.disconnect()
