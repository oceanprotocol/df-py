import random
from unittest.mock import patch
from enforce_typing import enforce_types
from typing import List
from util.predictoor.query import queryPredictoors


@enforce_types
def create_mock_response(statuses: List[str], payouts: List[float], users: List[str]):
    return {
        "data": {
            "predictPredictions": [
                {
                    "id": f"{user}-5520-0xbe5449a6a97ad46c8558a3356267ee5d2731ab5e",
                    "slot": {
                        "status": status,
                        "predictContract": {
                            "id": "0x1733696512e69cd0c4430f909dcbf54c54c15441"
                        },
                        "slot": "5520",
                    },
                    "user": {"id": user},
                    "payout": {"payout": str(payout)},
                    "block": 5459,
                }
                for status, payout, user in zip(statuses, payouts, users)
            ]
        }
    }


@patch("util.predictoor.query.submitQuery")
def test_queryPredictoors(mock_submitQuery):
    _statuses = ["Pending", "Paying", "Canceled"]
    _weights = [1, 4, 1]
    _count = 1

    users = [f"0x{i}000000000000000000000000000000000000000" for i in range(_count)]
    user_predictions = {user: {"total": 0, "correct": 0} for user in users}

    def generate_responses(n: int):
        responses = []
        for _ in range(n):
            payouts = [1.0 if random.random() > 0.4 else 0.0 for _ in range(_count)]
            statuses = random.choices(_statuses, weights=_weights, k=_count)
            response = create_mock_response(statuses, payouts, users)
            responses.append(response)

            # update stats
            for user, status, payout in zip(users, statuses, payouts):
                if status == "Paying":
                    user_predictions[user]["total"] += 1
                    if payout > 0:
                        user_predictions[user]["correct"] += 1

        responses.append(
            create_mock_response([], [], [])
        )  # empty response to simulate end of data
        return responses

    responses = generate_responses(10)
    mock_submitQuery.side_effect = responses

    predictoors = queryPredictoors(1, 2, 1)

    for user, predictions in user_predictions.items():
        if user in predictoors:
            predictor = predictoors[user]
            assert predictor.prediction_count == predictions["total"]
            assert predictor.correct_prediction_count == predictions["correct"]
            assert (
                predictor.accuracy == predictions["correct"] / predictions["total"]
                if predictions["total"] > 0
                else 0
            )

    mock_submitQuery.assert_called()
