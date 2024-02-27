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

