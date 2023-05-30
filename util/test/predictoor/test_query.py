import random
import brownie
from unittest.mock import patch
from enforce_typing import enforce_types
from typing import List
from util import networkutil
from util.predictoor.query import queryPredictoors

CHAINID = networkutil.DEV_CHAINID
chain = None

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
    _count = 100

    users = [f"0x{i}" for i in range(_count)]
    stats = {user: {"total": 0, "correct": 0} for user in users}

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
                    stats[user]["total"] += 1
                    if payout > 0:
                        stats[user]["correct"] += 1

        responses.append(
            create_mock_response([], [], [])
        )  # empty response to simulate end of data
        return responses

    responses = generate_responses(100)
    mock_submitQuery.side_effect = responses

    predictoors = queryPredictoors(1, 2, 1)

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


@enforce_types
def test_queryPredictoors_request():
    ST = 0 
    FIN = chain[-1].number
    predictoors = queryPredictoors(ST, FIN, CHAINID)
    assert predictoors


@enforce_types
def setup_function():
    global chain
    networkutil.connect(CHAINID)
    chain = brownie.network.chain

@enforce_types
def teardown_function():
    networkutil.disconnect()


