import random
from typing import List
from enforce_typing import enforce_types


@enforce_types
def create_mock_responses(n: int):
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

    responses = generate_responses(n)

    return responses, users, stats


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
                            "id": "0x1733696512e69cd0c4430f909dcbf54c54c15441",
                            "token": {"nft": {"owner": {"id": "0x0"}}},
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
