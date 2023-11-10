from unittest.mock import patch

import pytest
from web3 import Web3

from df_py.predictoor.predictoor_testutil import create_mock_responses
from df_py.predictoor.queries import (
    info_from_725,
    query_predictoors,
    key_to_725,
    value_from_725,
    info_from_725,
    value_to_725,
)
from df_py.util import networkutil

CHAINID = networkutil.DEV_CHAINID


@patch("df_py.predictoor.queries.submit_query")
def test_query_predictoors(mock_submit_query):
    responses, users, stats = create_mock_responses(100)
    mock_submit_query.side_effect = responses

    predictoors = query_predictoors(1, 2, CHAINID)

    for user in users:
        if stats[user]["total"] == 0:
            assert user not in predictoors
            continue
        user_total = stats[user]["total"]
        user_correct = stats[user]["correct"]
        assert predictoors[user].prediction_count == user_total
        assert predictoors[user].correct_prediction_count == user_correct
        assert predictoors[user].accuracy == user_correct / user_total

    mock_submit_query.assert_called()


@pytest.mark.skip(reason="Requires predictoor support in subgraph")
def test_query_predictoors_request():
    ST = 0
    FIN = chain[-1].number
    predictoors = query_predictoors(ST, FIN, CHAINID)
    assert predictoors is not None
    assert isinstance(predictoors, dict)


def test_key():
    key = "name"
    key725 = key_to_725(key)
    assert key725 == Web3.keccak(key.encode("utf-8")).hex()


def test_value():
    value = "ETH/USDT"
    value725 = value_to_725(value)
    value_again = value_from_725(value725)

    assert value == value_again
    assert value == Web3.to_text(hexstr=value725)


def test_info_from_725():
    info725_list = [
        {"key": key_to_725("pair"), "value": value_to_725("ETH/USDT")},
        {"key": key_to_725("timeframe"), "value": value_to_725("5m")},
    ]
    info_dict = info_from_725(info725_list)
    assert info_dict == {
        "pair": "ETH/USDT",
        "timeframe": "5m",
        "base": None,
        "quote": None,
        "source": None,
    }
