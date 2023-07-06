import random
from typing import Dict, Union
from unittest.mock import patch

import pytest

from df_py.predictoor.calc_rewards import calc_predictoor_rewards, filter_predictoors
from df_py.predictoor.models import Predictoor, PredictoorBase, Prediction
from df_py.util.constants import MIN_PREDICTIONS
from df_py.util.networkutil import DEV_CHAINID
from df_py.volume.calc_rewards import flatten_rewards

@pytest.fixture(autouse=True)
def mock_query_functions():
    with patch(
        "df_py.predictoor.calc_rewards.query_predictoor_contracts"
    ) as mock:
        mock.return_value = ["0xContract1", "0xContract2"]
        yield


def test_filter_predictoors():
    p1 = Predictoor("0x1")
    p1._prediction_count = MIN_PREDICTIONS - 1
    p2 = Predictoor("0x2")
    p2._prediction_count = MIN_PREDICTIONS
    p3 = Predictoor("0x3")
    p3._prediction_count = MIN_PREDICTIONS + 1
    predictoors = {"0x1": p1, "0x2": p2, "0x3": p3}

    filtered = filter_predictoors(predictoors)

    assert len(filtered) == 2
    assert "0x1" not in filtered
    assert "0x2" in filtered
    assert "0x3" in filtered


def test_calc_predictoor_rewards_no_predictions():
    predictoors: Dict[str, Predictoor] = {}

    rewards = calc_predictoor_rewards(predictoors, 100, DEV_CHAINID)

    for contract_rewards in rewards.values():
        assert len(contract_rewards) == 0


def test_calc_predictoor_rewards_one_prediction_not_eligible():
    p1 = Predictoor("0x1")
    for i in range(MIN_PREDICTIONS - 1):
        p1.add_prediction(Prediction(1, 1.0, "0xContract1"))

    predictoors = {"0x1": p1}

    rewards = calc_predictoor_rewards(predictoors, 100, DEV_CHAINID)

    for contract_rewards in rewards.values():
        assert len(contract_rewards) == 0


def test_calc_predictoor_rewards_one_prediction_eligible():
    p1 = Predictoor("0x1")

    for i in range(MIN_PREDICTIONS + 1):
        p1.add_prediction(Prediction(1, 1.0, "0xContract1"))

    predictoors = {"0x1": p1}

    rewards = calc_predictoor_rewards(predictoors, 200, DEV_CHAINID)

    total_rewards_for_p1 = sum(
        contract_rewards.get(p1.address, 0) for contract_rewards in rewards.values()
    )
    assert total_rewards_for_p1 == 100


def test_calc_predictoor_rewards_with_predictions():
    p1 = Predictoor("0x1")
    for i in range(5):
        p1.add_prediction(Prediction(1, 1.0, "0xContract1"))
    for i in range(MIN_PREDICTIONS):
        p1.add_prediction(Prediction(1, 0.0, "0xContract1"))

    p2 = Predictoor("0x2")
    for i in range(20):
        p2.add_prediction(Prediction(1, 1.0, "0xContract2"))
    for i in range(MIN_PREDICTIONS):
        p2.add_prediction(Prediction(1, 0.0, "0xContract2"))

    p3 = Predictoor("0x3")
    for i in range(5):
        p3.add_prediction(Prediction(1, 1.0, "0xContract2"))
    for i in range(MIN_PREDICTIONS):
        p3.add_prediction(Prediction(1, 0.0, "0xContract2"))
    predictoors = {"0x1": p1, "0x2": p2, "0x3": p3}

    rewards = calc_predictoor_rewards(predictoors, 100, DEV_CHAINID)

    assert len(rewards) == 2
    assert rewards["0xContract1"]["0x1"] == 50.0
    assert rewards["0xContract2"]["0x2"] == 40.0
    assert rewards["0xContract2"]["0x3"] == 10.0


def test_calc_predictoor_rewards_fuzz():
    predictoors = {}
    total_accuracy = 0
    for i in range(100):  # generate 100 predictoors
        address = f"0x{i}"
        p = Predictoor(address)
        prediction_count = random.randint(
            round(MIN_PREDICTIONS * 0.9), round(MIN_PREDICTIONS * 1.2)
        )
        correct_prediction_count = random.randint(0, prediction_count)
        for i in range(correct_prediction_count):
            p.add_prediction(Prediction(1, 1.0, "0xContract1"))
            p.add_prediction(Prediction(1, float(random.randint(0,1)), "0xContract2"))
        for i in range(prediction_count - correct_prediction_count):
            p.add_prediction(Prediction(1, 0.0, "0xContract1"))
            p.add_prediction(Prediction(1, 0.0, "0xContract2"))
        if p.prediction_count >= MIN_PREDICTIONS:
            total_accuracy += p.accuracy  # used to validate results in the end
        predictoors[address] = p

    tokens_avail = 1000

    rewards = calc_predictoor_rewards(predictoors, tokens_avail, DEV_CHAINID)

    # the rewards of each Predictoor should be proportionate to its accuracy
    total_accuracy_1 = sum([p.get_prediction_summary("0xContract1").correct_prediction_count for p in predictoors.values()])
    total_accuracy_2 = sum([p.get_prediction_summary("0xContract2").correct_prediction_count for p in predictoors.values()])
    for address, p in predictoors.items():
        if p.prediction_count < MIN_PREDICTIONS:
            assert rewards.get(address, 0) == 0
            continue
        acc1 = p.get_prediction_summary("0xContract1").correct_prediction_count
        acc2 = p.get_prediction_summary("0xContract2").correct_prediction_count
        expected_reward_1 = acc1 / total_accuracy_1 * tokens_avail / 2
        expected_reward_1 = acc2 / total_accuracy_2 * tokens_avail / 2
        assert (
            abs(rewards["0xContract1"].get(address, 0) - expected_reward_1) < 1e-6
        )  # allow for small floating point differences
        assert (
            abs(rewards["0xContract2"].get(address, 0) - expected_reward_2) < 1e-6
        )  # allow for small floating point differences

    # Sum of all rewards should be equal to tokens available
    print(rewards)
    print(flatten_rewards(rewards))
    assert (
        abs(sum(flatten_rewards(rewards).values()) - tokens_avail) < 1e-6
    )  # allow for small floating point differences
