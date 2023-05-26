from unittest.mock import patch
from util.predictoor.query import queryPredictoors


@patch("util.predictoor.query.submitQuery")
def test_queryPredictoors(mock_submitQuery):
    responses = [
        {
            "data": {
                "predictPredictions": [
                    {
                        "id": "1",
                        "slot": {"predictContract": "0x123", "slot": "1", "status": 1},
                        "user": {"id": "0x1"},
                        "payout": "0.5",
                        "block": 1000,
                    },
                    {
                        "id": "2",
                        "slot": {"predictContract": "0x123", "slot": "2", "status": 1},
                        "user": {"id": "0x2"},
                        "payout": "0",
                        "block": 1001,
                    },
                ]
            }
        },
        {"data": {"predictPredictions": []}},
    ]
    mock_submitQuery.side_effect = responses

    predictoors = queryPredictoors(1000, 1001, 1)
    assert len(predictoors) == 2
    assert predictoors["0x1"].get_prediction_count() == 1
    assert predictoors["0x2"].get_prediction_count() == 1
    assert predictoors["0x1"].get_correct_prediction_count() == 1
    assert predictoors["0x2"].get_correct_prediction_count() == 0
    assert predictoors["0x1"].get_accuracy() == 0
    assert predictoors["0x2"].get_accuracy() == 0
    mock_submitQuery.assert_called()
