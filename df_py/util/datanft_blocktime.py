import os
import json
from typing import Dict, Optional, Union
from df_py.util.http_provider import get_web3_connection_provider
from enforce_typing import enforce_types

from web3 import Web3
from df_py.util.contract_base import ContractBase


@enforce_types
def _set_data(w3, nft_addr: str, field_label: str, data: str) -> bool:
    field_label_hash = Web3.keccak(text=field_label)
    field_value_bytes = data.encode()
    contract_instance = ContractBase(w3, "ERC721Template", nft_addr)
    tx = contract_instance.contract.functions.setNewData(
        field_label_hash, field_value_bytes
    ).transact()
    receipt = w3.eth.wait_for_transaction_receipt(tx)
    return receipt is not None and receipt["status"] == 1


@enforce_types
def _read_data(w3, nft_addr: str, field_label: str) -> str:
    field_label_hash = Web3.keccak(text=field_label)
    contract_instance = ContractBase(w3, "ERC721Template", nft_addr)
    value = contract_instance.contract.functions.getData(field_label_hash).call()
    value_str = value.decode("utf-8")
    return value_str


@enforce_types
def _get_w3_object():
    # DataNFT that holds the block numbers is deployed on Polygon
    rpc_url = os.getenv("POLYGON_RPC_URL")
    return Web3(get_web3_connection_provider(rpc_url))


@enforce_types
def _set_blocknumber_data(
    nft_addr: str, from_account, blocknumbers: Dict[str, int], week_number: str, w3=None
) -> bool:
    w3 = _get_w3_object() if w3 is None else w3
    w3.eth.default_account = from_account
    data = json.dumps(blocknumbers)
    return _set_data(w3, nft_addr, week_number, data)


@enforce_types
def _read_blocknumber_data(nft_addr: str, week_number: str, w3) -> Dict[str, int]:
    w3 = _get_w3_object() if w3 is None else w3
    data = _read_data(w3, nft_addr, week_number)
    print("DATA READ:", data)
    if data == "":
        return {}
    return json.loads(data)


@enforce_types
def get_block_number_from_datanft(
    chainid: Union[str, int], week_number: Union[str, int], w3=None
) -> int:
    data = _read_blocknumber_data(os.getenv("DATANFT_ADDR"), str(week_number), w3)
    return data.get(str(chainid), 0)


@enforce_types
def set_blocknumber_to_datanft(
    chainid: int, from_account, blocknumber: int, week_number: Union[str, int], w3=None
) -> bool:
    nft_addr = os.getenv("DATANFT_ADDR")
    data = _read_blocknumber_data(nft_addr, str(week_number), w3)
    data[chainid] = blocknumber
    return _set_blocknumber_data(nft_addr, from_account, data, str(week_number), w3)
