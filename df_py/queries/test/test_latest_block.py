from unittest.mock import patch

from enforce_typing import enforce_types
import pytest

from df_py.queries.latest_block import (
    get_last_block,
    wait_to_latest_block,
)


@enforce_types
def test_get_last_block():
    with patch("df_py.queries.latest_block.submit_query") as submit_query_mock:
        submit_query_mock.return_value = {"data": {"_meta": {"block": {"number": 123}}}}

        assert get_last_block(8996) == 123

    with patch("df_py.queries.latest_block.submit_query") as submit_query_mock:
        submit_query_mock.return_value = {
            "errors": [{"message": "something went wrong"}]
        }

        with pytest.raises(KeyError):
            assert get_last_block(8996)


def test_wait_to_latest_block(w3):
    block_number = w3.eth.get_block("latest")["number"]
    with patch("df_py.queries.latest_block.get_last_block") as mock:
        mock.return_value = block_number - 1

        with pytest.raises(Exception):
            wait_to_latest_block(8996, 4)

        assert mock.call_count == 2

    block_number = w3.eth.get_block("latest")["number"]
    with patch("df_py.queries.latest_block.get_last_block") as mock:
        mock.return_value = block_number

        wait_to_latest_block(8996, 4)
        assert mock.call_count == 1


def test_obsolete_chain_id():
    with patch("df_py.queries.latest_block.get_last_block") as mock:
        # obsolete chain id so nothing gets called
        wait_to_latest_block(246, 4)
        assert mock.call_count == 0
