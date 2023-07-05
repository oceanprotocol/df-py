import os
import warnings

import brownie
from enforce_typing import enforce_types

from df_py.util.constants import CONTRACTS, MULTISIG_ADDRS

_BARGE_ADDRESS_FILE = "~/.ocean/ocean-contracts/artifacts/address.json"

# Development chainid is from brownie, rest are from chainlist.org
# Chain values to fit Ocean subgraph urls as given in
# https://v3.docs.oceanprotocol.com/concepts/networks/

_RAW_CHAIN_DATA = [
    (8996, "development", "OCEAN"),
    (1, "mainnet", "ETH"),
    (5, "goerli", "ETH"),
    (137, "polygon", "MATIC"),
    (80001, "mumbai", "MATIC"),
    (23294, "oasis_sapphire", "ROSE"),
    (23295, "oasis_sapphire_testnet", "ROSE"),
]

# chainids and names must be unique. Token symbols don't need to be
__chainids_list = [x[0] for x in _RAW_CHAIN_DATA]
assert len(__chainids_list) == len(set(__chainids_list)), "need unique chainids"

__names_list = [x[1] for x in _RAW_CHAIN_DATA]
assert len(__names_list) == len(set(__names_list)), "need unique names"

# mappings used later
_CHAINID_TO_NETWORK = {x[0]: x[1] for x in _RAW_CHAIN_DATA}
_CHAINID_TO_NATIVE_TOKEN = {x[0]: x[2] for x in _RAW_CHAIN_DATA}
_CHAINID_TO_ADDRS = {x: f"0x{y}" for x, y in _CHAINID_TO_NETWORK.items()}
_ADDRS_TO_SYMBOL = {}
for chainid, addr in _CHAINID_TO_ADDRS.items():
    _ADDRS_TO_SYMBOL[addr] = _CHAINID_TO_NATIVE_TOKEN[chainid]


_NETWORK_TO_CHAINID = {
    network: chainID for chainID, network in _CHAINID_TO_NETWORK.items()
}

DEV_CHAINID = _NETWORK_TO_CHAINID["development"]


@enforce_types
def chain_id_to_address_file(chainID: int) -> str:  # pylint: disable=unused-argument
    """Returns the address file for a given chainID"""
    return os.path.expanduser(_BARGE_ADDRESS_FILE)


@enforce_types
def chain_id_to_subgraph_uri(chainID: int) -> str:
    """Returns the subgraph URI for a given chainID"""
    sg = "/subgraphs/name/oceanprotocol/ocean-subgraph"
    if chainID == DEV_CHAINID:
        return "http://127.0.0.1:9000" + sg

    network_str = chain_id_to_network(chainID)
    return f"https://v4.subgraph.{network_str}.oceanprotocol.com" + sg


@enforce_types
def chain_id_to_multisig_uri(chainID: int) -> str:
    """Returns the multisig API URI for a given chainID"""
    network_str = chain_id_to_network(chainID)
    return f"https://safe-transaction-{network_str}.safe.global"


@enforce_types
def chain_id_to_multisig_addr(chainID: int) -> str:
    """Returns the multisig address for a given chainID"""
    if chainID not in MULTISIG_ADDRS:
        # pylint: disable=broad-exception-raised
        raise Exception(f"Multisig address not known for chainID {chainID}")
    return MULTISIG_ADDRS[chainID]


@enforce_types
def chain_id_to_network(chainID: int) -> str:
    """Returns the network name for a given chainID"""
    return _CHAINID_TO_NETWORK[chainID]


@enforce_types
def network_to_chain_id(network: str) -> int:
    """Returns the chainID for a given network name"""
    return _NETWORK_TO_CHAINID[network]


@enforce_types
def get_latest_block(chainID) -> int:
    network = brownie.network
    prev = None
    if not network.is_connected():
        connect(chainID)
    else:
        prev = network.chain.id
        if prev != chainID:
            disconnect()
            connect(chainID)
    lastBlock = network.chain.height
    if prev is not None:
        disconnect()
        connect(prev)
    return lastBlock


@enforce_types
def connect_dev():
    connect(DEV_CHAINID)


@enforce_types
def connect(chainID: int):
    network = brownie.network
    if network.is_connected():
        disconnect()  # call networkutil.disconnect(), *NOT* brownie directly
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message=".*Development network has a block height of*",
        )
        network_name = chain_id_to_network(chainID)
        try:
            network.connect(network_name)
        except KeyError as e:
            if network_name != "mumbai":
                raise e

            network.connect("polygon-test")


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
