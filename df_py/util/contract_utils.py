#
# Copyright 2023 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

import solcx
from enforce_typing import enforce_types
from solcx import compile_source
from web3.contract import Contract
from web3.main import Web3

GANACHE_URL = "http://127.0.0.1:8545"


@enforce_types
def get_contract_definition(path: str) -> Dict[str, Any]:
    """Returns the abi JSON for a contract name."""
    path = os.path.join(Path.cwd(), f"build/contracts/{path}.json")
    path = Path(path).expanduser().resolve()

    if not path.exists():
        raise TypeError("Contract name does not exist in artifacts.")

    with open(path) as f:
        return json.load(f)


@enforce_types
def get_contract_source(path: str) -> Dict[str, Any]:
    """Returns the abi JSON for a contract name."""
    path = os.path.join(Path.cwd(), f"contracts/{path}.sol")
    path = Path(path).expanduser().resolve()

    if not path.exists():
        raise TypeError("Contract name does not exist in artifacts.")

    return open(path, "r").read()


@enforce_types
def load_contract(web3: Web3, path: str, address: Optional[str]) -> Contract:
    """Loads a contract using its name and address."""
    contract_definition = get_contract_definition(path)
    abi = contract_definition["abi"]
    bytecode = contract_definition["bytecode"]

    return web3.eth.contract(address=address, abi=abi, bytecode=bytecode)


@enforce_types
def deploy_contract(web3: Web3, path: str, constructor_args: list) -> Contract:
    contract_source = get_contract_source(path)
    contract_base_name = path if "/" not in path else path.split("/")[-1]
    solcx.install_solc(version="0.8.12")
    solcx.set_solc_version("0.8.12")

    remapping = {
        "OpenZeppelin/openzeppelin-contracts@4.2.0": "node_modules/@openzeppelin",
        "interfaces": "contracts/interfaces",
    }

    compiled_sol = compile_source(
        contract_source, output_values=["abi", "bin"], import_remappings=remapping
    )

    # popitems succesively because the compiler also
    # returns the interfaces of imported contracts e.g. OpenZeppelin
    contract_name = ""
    while contract_name.lower() != contract_base_name.lower():
        contract_id, contract_interface = compiled_sol.popitem()
        contract_name = contract_id.split(":")[1]

    bytecode = contract_interface["bin"]
    abi = contract_interface["abi"]

    contract = web3.eth.contract(abi=abi, bytecode=bytecode)
    tx_hash = contract.constructor(*constructor_args).transact()

    tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash)

    return web3.eth.contract(address=tx_receipt.contractAddress, abi=abi)


@enforce_types
def get_contracts_addresses_all_networks(config: dict):
    """Get addresses, across *all* networks, from info in ADDRESS_FILE"""
    address_file = config.get("ADDRESS_FILE")
    address_file = os.path.expanduser(address_file) if address_file else None

    if not address_file or not os.path.exists(address_file):
        raise Exception(f"Could not find address_file={address_file}.")
    with open(address_file) as f:
        addresses = json.load(f)

    return addresses


@enforce_types
def get_contracts_addresses(config: dict) -> Optional[Dict[str, str]]:
    """Get addresses for given NETWORK_NAME, from info in ADDRESS_FILE"""
    network_name = config["NETWORK_NAME"]

    addresses = get_contracts_addresses_all_networks(config)

    network_addresses = [val for key, val in addresses.items() if key == network_name]

    if not network_addresses:
        address_file = config.get("ADDRESS_FILE")
        raise Exception(
            f"Address not found for network_name={network_name}."
            f" Please check your address_file={address_file}."
        )

    return _checksum_contract_addresses(network_addresses=network_addresses[0])


@enforce_types
# Check singnet/snet-cli#142 (comment). You need to provide a lowercase address then call web3.to_checksum_address()
# for software safety.
def _checksum_contract_addresses(
    network_addresses: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    for key, value in network_addresses.items():
        if key == "chainId":
            continue
        if isinstance(value, int):
            continue
        if isinstance(value, dict):
            for k, v in value.items():
                value.update({k: Web3.to_checksum_address(v.lower())})
        else:
            network_addresses.update({key: Web3.to_checksum_address(value.lower())})

    return network_addresses
