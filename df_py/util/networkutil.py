import os
from typing import Union

from enforce_typing import enforce_types

from df_py.util.constants import CONTRACTS, MULTISIG_ADDRS
from df_py.util.oceanutil import get_rpc_url, get_web3

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
def chain_id_to_web3(chainID: int) -> str:
    """Returns the web3 instance for a given chainID"""
    network_name = _CHAINID_TO_NETWORK[chainID]
    return get_web3(get_rpc_url(network_name))


@enforce_types
def network_to_chain_id(network: str) -> int:
    """Returns the chainID for a given network name"""
    return _NETWORK_TO_CHAINID[network]


@enforce_types
def send_ether(
    web3, from_wallet, to_address: str, amount: Union[int, float]
):
    chain_id = web3.eth.chain_id
    tx = {
        "from": from_wallet.address,
        "to": to_address,
        "value": amount,
        "chainId": chain_id,
        "nonce": web3.eth.get_transaction_count(from_wallet.address),
        "type": 2,
    }
    tx["gas"] = web3.eth.estimate_gas(tx)

    priority_fee = web3.eth.max_priority_fee
    base_fee = web3.eth.get_block("latest")["baseFeePerGas"]

    tx["maxPriorityFeePerGas"] = priority_fee
    tx["maxFeePerGas"] = base_fee * 2 + priority_fee

    signed_tx = web3.eth.account.sign_transaction(tx, from_wallet._private_key)
    tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)

    return web3.eth.wait_for_transaction_receipt(tx_hash)
