from unittest.mock import patch

import pytest

from df_py.util import graphutil


def test_get_last_block():
    with patch("df_py.util.graphutil.submit_query") as submit_query_mock:
        submit_query_mock.return_value = {"data": {"_meta": {"block": {"number": 123}}}}

        assert graphutil.get_last_block(8996) == 123

    with patch("df_py.util.graphutil.submit_query") as submit_query_mock:
        submit_query_mock.return_value = {
            "errors": [{"message": "something went wrong"}]
        }

        with pytest.raises(KeyError):
            assert graphutil.get_last_block(8996)


def test_wait_to_latest_block(w3):
    block_number = w3.eth.get_block("latest")["number"]
    with patch.object(graphutil, "get_last_block") as get_last_block_mock:
        get_last_block_mock.return_value = block_number - 1

        with pytest.raises(Exception):
            graphutil.wait_to_latest_block(8996, 4)

        assert get_last_block_mock.call_count == 2

    block_number = w3.eth.get_block("latest")["number"]
    with patch.object(graphutil, "get_last_block") as get_last_block_mock:
        get_last_block_mock.return_value = block_number

        graphutil.wait_to_latest_block(8996, 4)
        assert get_last_block_mock.call_count == 1


def test_obsolete_chain_id():
    with patch.object(graphutil, "get_last_block") as mock:
        # obsolete chain id so nothing gets called
        graphutil.wait_to_latest_block(246, 4)
        assert mock.call_count == 0
