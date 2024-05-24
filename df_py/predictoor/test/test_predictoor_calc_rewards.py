import random
from typing import Dict, Union
from unittest.mock import patch

import pytest

from df_py.predictoor.calc_rewards import (
    aggregate_predictoor_rewards,
    calc_predictoor_rewards,
)
from df_py.predictoor.models import Prediction, Predictoor, PredictoorBase
from df_py.util.networkutil import DEV_CHAINID
from df_py.util.reward_shaper import RewardShaper


@pytest.fixture(autouse=True)
def mock_query_functions():
    with patch("df_py.predictoor.calc_rewards.query_predictoor_contracts") as mock:
        mock.return_value = {"0xContract1": "", "0xContract2": ""}
        yield


def test_calc_predictoor_rewards_no_predictions():
    predictoors: Dict[str, Predictoor] = {}  # type: ignore

    rewards = calc_predictoor_rewards(predictoors, 100, DEV_CHAINID)

    for contract_rewards in rewards.values():
        assert len(contract_rewards) == 0


def test_calc_predictoor_rewards_one_predictoor():
    p1 = Predictoor("0x1")

    for i in range(10):
        p1.add_prediction(Prediction(1, 1.0, 0.1, "0xContract1"))

    predictoors = {"0x1": p1}

    rewards = calc_predictoor_rewards(predictoors, 200, DEV_CHAINID)

    total_rewards_for_p1 = sum(
        contract_rewards.get(p1.address, 0) for contract_rewards in rewards.values()
    )

    # 100 because there are 2 predictoor contracts in the network
    assert total_rewards_for_p1 == 100


def test_calc_predictoor_rewards_small_amount_two_predictoors():
    p1 = Predictoor("0x1")

    for _ in range(1):
        p1.add_prediction(Prediction(1, 1e-15, 1e-15, "0xContract1"))

    p2 = Predictoor("0x2")

    for _ in range(10000):
        p2.add_prediction(Prediction(1, 200.0, 100.0, "0xContract1"))

    predictoors = {"0x1": p1, "0x2": p2}

    rewards = calc_predictoor_rewards(predictoors, 200, DEV_CHAINID)

    total_rewards_for_p1 = sum(
        contract_rewards.get(p1.address, 0) for contract_rewards in rewards.values()
    )
    total_rewards_for_p2 = sum(
        contract_rewards.get(p2.address, 0) for contract_rewards in rewards.values()
    )

    # 100 because there are 2 predictoor contracts in the network
    assert total_rewards_for_p1 == 0
    assert total_rewards_for_p2 == 100


def test_calc_predictoor_rewards_with_predictions():
    p1 = Predictoor("0x1")
    # profit = 1.0
    for i in range(7):
        p1.add_prediction(Prediction(1, 1.0, 0.5, "0xContract1"))
    for i in range(5):
        p1.add_prediction(Prediction(1, 0.0, 0.5, "0xContract1"))

    p2 = Predictoor("0x2")
    # profit = 2.5
    for i in range(15):
        p2.add_prediction(Prediction(1, 1.0, 0.5, "0xContract2"))
    for i in range(10):
        p2.add_prediction(Prediction(1, 0.0, 0.5, "0xContract2"))

    p3 = Predictoor("0x3")
    # profit = 1.5
    for i in range(8):
        p3.add_prediction(Prediction(1, 1.0, 0.5, "0xContract2"))
    for i in range(5):
        p3.add_prediction(Prediction(1, 0.0, 0.5, "0xContract2"))
    predictoors = {"0x1": p1, "0x2": p2, "0x3": p3}

    rewards = calc_predictoor_rewards(predictoors, 100, DEV_CHAINID)

    assert len(rewards) == 2
    assert rewards["0xContract1"]["0x1"] == 50.0
    assert rewards["0xContract2"]["0x2"] == 31.25
    assert rewards["0xContract2"]["0x3"] == 18.75


def test_negative_revenue():
    p1 = Predictoor("0x1")
    for _ in range(5):
        # profit = 0.5 * 5
        p1.add_prediction(Prediction(1, 1.0, 0.5, "0xContract1"))
    for _ in range(5):
        # profit = -2.0 * 5
        p1.add_prediction(Prediction(1, 0.0, 2.0, "0xContract1"))

    summary = p1.get_prediction_summary("0xContract1")
    assert summary.total_revenue == -7.5


def test_reward_calculation_with_negative():
    p1 = Predictoor("0x1")
    for _ in range(5):
        p1.add_prediction(Prediction(1, 1.0, 0.5, "0xContract1"))
    for _ in range(5):
        p1.add_prediction(Prediction(1, 0.0, 2.0, "0xContract1"))

    rewards = calc_predictoor_rewards({"0x1": p1}, 1000, DEV_CHAINID)
    assert len(rewards["0xContract1"]) == 0
    assert len(rewards["0xContract2"]) == 0


def test_calc_predictoor_rewards_fuzz():
    predictoors = {}
    for i in range(100):  # generate 100 predictoors
        address = f"0x{i}"
        p = Predictoor(address)
        prediction_count = random.randint(1000, 2000)
        correct_prediction_count = random.randint(0, prediction_count)
        for i in range(correct_prediction_count):
            p.add_prediction(Prediction(1, 10.0, random.random() * 10, "0xContract1"))
            p.add_prediction(Prediction(1, 10.0, random.random() * 10, "0xContract2"))
        for i in range(prediction_count - correct_prediction_count):
            p.add_prediction(Prediction(1, 0.0, random.random() * 10, "0xContract1"))
            p.add_prediction(Prediction(1, 0.0, random.random() * 10, "0xContract2"))
        predictoors[address] = p

    tokens_avail = 1000

    rewards = calc_predictoor_rewards(predictoors, tokens_avail, DEV_CHAINID)

    # the rewards of each Predictoor should be proportionate to their revenue
    total_revenue_1 = 0
    total_revenue_2 = 0
    for p in predictoors.values():
        summary1 = p.get_prediction_summary("0xContract1")
        summary2 = p.get_prediction_summary("0xContract2")

        # ignore negatives
        total_revenue_1 += max(summary1.total_revenue, 0)
        total_revenue_2 += max(summary2.total_revenue, 0)

    for address, p in predictoors.items():
        rev1 = p.get_prediction_summary("0xContract1").total_revenue
        rev2 = p.get_prediction_summary("0xContract2").total_revenue
        expected_reward_1 = rev1 / total_revenue_1 * tokens_avail / 2
        expected_reward_2 = rev2 / total_revenue_2 * tokens_avail / 2
        expected_reward_1 = 0 if rev1 < 0 else expected_reward_1
        expected_reward_2 = 0 if rev2 < 0 else expected_reward_2
        assert (
            abs(rewards["0xContract1"].get(address, 0) - expected_reward_1) < 1e-6
        )  # allow for small floating point differences
        assert (
            abs(rewards["0xContract2"].get(address, 0) - expected_reward_2) < 1e-6
        )  # allow for small floating point differences

    # Sum of all rewards should be equal to tokens available
    print(rewards)
    print(RewardShaper.flatten(rewards))
    assert (
        abs(sum(RewardShaper.flatten(rewards).values()) - tokens_avail) < 1e-6
    )  # allow for small floating point differences


def test_aggregate_rewards():
    predictoor_rewards = {
        "contract1": {"predictoor1": 10.0, "predictoor2": 5.0, "predictoor3": 7.0},
        "contract2": {"predictoor1": 3.0, "predictoor2": 2.0, "predictoor4": 4.0},
    }

    result = aggregate_predictoor_rewards(predictoor_rewards)

    expected_output = {
        "predictoor1": 13.0,
        "predictoor2": 7.0,
        "predictoor3": 7.0,
        "predictoor4": 4.0,
    }

    assert result == expected_output


def test_calc_predictoor_different_slots():
    p1 = Predictoor("0x1")
    p2 = Predictoor("0x2")
    p3 = Predictoor("0x3")

    p1.add_prediction(Prediction(1, 1.0, 0.1, "0xContract1"))
    p2.add_prediction(Prediction(1, 1.0, 0.1, "0xContract1"))
    p3.add_prediction(Prediction(1, 1.0, 0.1, "0xContract1"))
    p1.add_prediction(Prediction(3, 1.0, 0.1, "0xContract1"))
    p3.add_prediction(Prediction(3, 1.0, 0.1, "0xContract1"))
    p1.add_prediction(Prediction(2, 1.0, 0.1, "0xContract1"))
    p2.add_prediction(Prediction(2, 1.0, 0.1, "0xContract1"))
    p2.add_prediction(Prediction(5, 1.0, 0.1, "0xContract1"))


    # p1 and p2 and p3 will share slot 1 reward
    # p1 and p3 will share slot 3
    # p1 and p2 will share slot 2
    # p2 will have slot 5 to itself

    # total of 4 slots, 100 rewards, 25 per each slot
    p1_expected = 25 / 3 + 25 / 2 + 25 / 2
    p2_expected = 25 / 3 + 25 / 2 + 25
    p3_expected = 25 / 3 + 25 / 2

    predictoors = {"0x1": p1, "0x2": p2, "0x3": p3}

    rewards = calc_predictoor_rewards(predictoors, 200, DEV_CHAINID)

    total_rewards_for_p1 = sum(
        contract_rewards.get(p1.address, 0) for contract_rewards in rewards.values()
    )
    total_rewards_for_p2 = sum(
        contract_rewards.get(p2.address, 0) for contract_rewards in rewards.values()
    )
    total_rewards_for_p3 = sum(
        contract_rewards.get(p3.address, 0) for contract_rewards in rewards.values()
    )

    assert total_rewards_for_p1 == pytest.approx(p1_expected)
    assert total_rewards_for_p2 == pytest.approx(p2_expected)
    assert total_rewards_for_p3 == pytest.approx(p3_expected)