from df_py.util.blocktime import get_st_block
import pytest
import os
from unittest.mock import patch
from df_py.util.datanft_blocktime import (
    _get_w3_object,
    _read_blocknumber_data,
    _read_data,
    _set_blocknumber_data,
    _set_data,
    get_block_number_from_datanft,
    set_blocknumber_to_datanft,
)
from df_py.util.oceanutil import create_data_nft


def test_datanft_write_and_read(w3, account0):
    CHAIN_ID = 42

    # Read the block number while it is not set, should return 0
    block_number = get_block_number_from_datanft(CHAIN_ID, w3)
    assert block_number == 0, "non-set block number must be 0"

    assert set_blocknumber_to_datanft(
        CHAIN_ID, account0.address, 100, w3
    ), "Failed to set block number data"

    # Read the block number again, should return 100
    block_number = get_block_number_from_datanft(CHAIN_ID, w3)
    assert block_number == 100, "block number must be 100"

def test_multiple_chainids_write_and_read(w3, account0):
    chain_ids_and_block_numbers = {
        1: 1000,
        2: 2000,
        3: 3000,
    }

    for chain_id, block_number in chain_ids_and_block_numbers.items():
        assert set_blocknumber_to_datanft(
            chain_id, account0.address, block_number, w3
        ), f"Failed to set block number for chain ID {chain_id}"

    for chain_id, expected_block_number in chain_ids_and_block_numbers.items():
        actual_block_number = get_block_number_from_datanft(chain_id, w3)
        assert (
            actual_block_number == expected_block_number
        ), f"Block number for chain ID {chain_id} must be {expected_block_number}"


def test_overwrite_existing_data(w3, account0):
    CHAIN_ID = 42
    NEW_BLOCK_NUMBER = 200

    # Set initial block number
    set_blocknumber_to_datanft(CHAIN_ID, account0.address, 100, w3)
    # Overwrite with a new block number
    assert set_blocknumber_to_datanft(
        CHAIN_ID, account0.address, NEW_BLOCK_NUMBER, w3
    ), "Failed to overwrite block number data"

    # Read back the overwritten block number
    block_number = get_block_number_from_datanft(CHAIN_ID, w3)
    assert block_number == NEW_BLOCK_NUMBER, "Overwritten block number must be 200"


def test_read_nonexistent_chainid(w3):
    NON_EXISTENT_CHAIN_ID = 999

    # Attempt to read a block number for a non-existent chain ID
    block_number = get_block_number_from_datanft(NON_EXISTENT_CHAIN_ID, w3)
    assert block_number == 0, "Block number for a non-existent chain ID must be 0"


@patch.dict(os.environ, {"POLYGON_RPC_URL": "http://localhost:8545"})
def test_get_w3_object():
    w3 = _get_w3_object()
    assert w3.is_connected(), "Web3 object is not connected"

