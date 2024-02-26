import os
import json
from typing import Dict

from web3 import Web3
from df_py.util.contract_base import ContractBase

def _set_data(w3, nft_addr: str, field_label: str, data: str) -> bool:
    field_label_hash = Web3.keccak(text=field_label)
    field_value_bytes = field_value.encode() 
    contract_instance = ContractBase(w3, "ERC721Template", constructor_args=[])
    tx = contract_instance.functions.setNewData(
        field_label_hash, field_value_bytes
    ).transact()
    receipt = self.config.w3.eth.wait_for_transaction_receipt(tx)
    return receipt is not None and receipt["status"] == 1


def _read_data(w3, nft_addr: str, field_label: str) -> str:
    field_label_hash = Web3.keccak(text=field_label)
    field_value_bytes = field_value.encode() 
    contract_instance = ContractBase(w3, "ERC721Template", constructor_args=[])
    value = contract_instance.functions.getData(
        field_label_hash
    ).call()

    value_str = value.decode("utf-8")
    return value_str

def set_blocknumber_data(w3, nft_addr: str, blocknumbers: Dict[int, int]) -> bool:
    data = json.dumps(blocknumbers)
    return _set_data(w3, nft_addr, "block_numbers", data)

def _read_blocknumber_data(w3, nft_addr: str) -> Dict[int, int]:
    data = _read_data(w3, nft_addr, "block_numbers")
    return json.loads(data)

def get_block_number_from_datanft(w3, chainid: int) -> int:
    data = _read_blocknumber_data(w3, os.getenv("DATANFT_ADDR"))
    return data.get(chainid)