import brownie
import pytest
from unittest.mock import patch
from enforce_typing import enforce_types
from util import networkutil
from util.predictoor.query import queryPredictoors
from util.predictoor.predictoor_testutil import create_mock_responses

CHAINID = networkutil.DEV_CHAINID
chain = None


@patch("util.predictoor.query.submitQuery")
def test_queryPredictoors(mock_submitQuery):
    responses, users, stats = create_mock_responses(100)
    mock_submitQuery.side_effect = responses

    predictoors = queryPredictoors(1, 2, CHAINID)

    for user in users:
        if stats[user]["total"] == 0:
            assert user not in responses
            continue
        user_total = stats[user]["total"]
        user_correct = stats[user]["correct"]
        assert predictoors[user].prediction_count == user_total
        assert predictoors[user].correct_prediction_count == user_correct
        assert predictoors[user].accuracy == user_correct / user_total

    mock_submitQuery.assert_called()


@pytest.mark.skip(reason="Requires predictoor support in subgraph")
def test_queryPredictoors_request():
    ST = 0
    FIN = chain[-1].number
    predictoors = queryPredictoors(ST, FIN, CHAINID)
    assert predictoors != None
    assert isinstance(predictoors, dict)


@enforce_types
def setup_function():
    global chain
    networkutil.connect(CHAINID)
    chain = brownie.network.chain


@enforce_types
def teardown_function():
    networkutil.disconnect()
