import os

import brownie
from enforce_typing import enforce_types

from util.constants import BROWNIE_PROJECT as B
from util.constants import CONTRACTS

_BARGE_ADDRESS_FILE = "~/.ocean/ocean-contracts/artifacts/address.json"

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
    return os.path.expanduser(_BARGE_ADDRESS_FILE)


@enforce_types
def chainIdToSubgraphUri(chainID: int) -> str:
    """Returns the subgraph URI for a given chainID"""
    sg = "/subgraphs/name/oceanprotocol/ocean-subgraph"
    network_str = chainIdToNetwork(chainID)
    if chainID == DEV_CHAINID:
        return "http://127.0.0.1:9000" + sg
    elif " " not in network_str:
        return f"https://v4.subgraph.{network_str.lower()}.oceanprotocol.com"+sg
    else:
        raise NotImplementedError("Don't yet support {network_str}")

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


#@enforce_types
def disconnect():
    network = brownie.network
    if not network.is_connected():
        return
    
    chainID = network.chain.id
    if chainID in CONTRACTS:
        del CONTRACTS[chainID]

    if chainID == DEV_CHAINID:
        network.disconnect()
    else:
        #workaround for https://github.com/eth-brownie/brownie/issues/1144
        #in file venv/lib/python3.8/site-packages/brownie/network/state.py
        #   function: _remove_contract()
        #   code: del _contract_map[contract.address]
        #When it calls _remove_contract():
        # - First time, it deletes _contract_map items
        # - After that, it can't find them, so gives KeyError

        #mimic brownie/network/main.py::disconnect(),
        # except bypass _remove_contract() to avoid KeyError
        rpc = network.rpc
        web3 = brownie.web3
        kill_rpc = True
        #network.CONFIG.clear_active() #bypass remove_contract()
        if kill_rpc and rpc.is_active():
            if rpc.is_child():
                rpc.kill()
        web3.disconnect()
        #_notify_registry(0) #bypass remove_contract()

        #Before brownie shuts down, it calls _remove_contract() again
        #  But _contract_map items are already deleted. Solve by
        #  reinserting 'None' items in to _contract_map        
        for contract in [x for v in B._containers.values() for x in v._contracts]:
            network.state._contract_map[contract.address] = None
        for container in B._containers.values():
            container._contracts.clear()
        B._containers.clear()
