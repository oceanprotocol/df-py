from unittest.mock import patch
from util.predictoor.query import queryPredictoors


def test_queryPredictoors():
    fake_result = {
        "data": {
            "predictPredictions": [
                {
                    "id": "1",
                    "slot": {"predictContract": "0x123", "slot": "1", "status": 1},
                    "user": {"id": "0x456"},
                    "payout": "0.5",
                    "block": 1000,
                },
                {
                    "id": "2",
                    "slot": {"predictContract": "0x123", "slot": "2", "status": 1},
                    "user": {"id": "0x789"},
                    "payout": "0",
                    "block": 1001,
                },
            ]
        }
    }

    # Mock the submitQuery function to return the fake result
    with patch("util.graphutil.submitQuery", return_value=fake_result):
        predictoors = queryPredictoors(1000, 1001, 1)
        assert len(predictoors) == 2
