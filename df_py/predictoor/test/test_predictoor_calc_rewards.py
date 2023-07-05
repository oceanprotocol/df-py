import random
from typing import Dict, Union
from unittest.mock import patch

import pytest

from df_py.predictoor.calc_rewards import calc_predictoor_rewards, filter_predictoors
from df_py.predictoor.models import Predictoor, PredictoorBase
from df_py.util.constants import MIN_PREDICTIONS
from df_py.util.networkutil import DEV_CHAINID


@pytest.fixture(autouse=True)
def mock_query_functions():
    with patch(
        "df_py.predictoor.queries.query_predictoor_contracts",
        ["0xContract1", "0xContract2"],
    ):
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
        p1.add_prediction(Prediction(1, 1.0, "0xContract2"))
    for i in range(MIN_PREDICTIONS):
        p1.add_prediction(Prediction(1, 0.0, "0xContract2"))

    p3 = Predictoor("0x3")
    for i in range(5):
        p1.add_prediction(Prediction(1, 1.0, "0xContract2"))
    for i in range(MIN_PREDICTIONS):
        p1.add_prediction(Prediction(1, 0.0, "0xContract2"))
    predictoors = {"0x1": p1, "0x2": p2, "0x3": p3}

    rewards = calc_predictoor_rewards(predictoors, 100)

    assert len(rewards) == 2
    assert rewards["0x1"] == 50.0
    assert rewards["0x2"] == 40.0
    assert rewards["0x3"] == 10.0


def test_calc_predictoor_rewards_fuzz():
    predictoors = {}
    total_accuracy = 0
    for i in range(100):  # generate 100 predictoors
        address = f"0x{i}"
        p = Predictoor(address)
        prediction_count = random.randint(
            round(MIN_PREDICTIONS * 0.9), round(MIN_PREDICTIONS * 1.2)
        )
        correct_prediction_count = random.randint(0, p._prediction_count)
        for i in range(correct_prediction_count):
            p.add_prediction(Prediction(1, 1.0, "0xContract1"))
        for i in range(prediction_count - correct_prediction_count):
            p.add_prediction(Prediction(1, 0.0, "0xContract1"))
        if p.prediction_count >= MIN_PREDICTIONS:
            total_accuracy += p.accuracy  # used to validate results in the end
        predictoors[address] = p

    tokens_avail = 1000

    rewards = calc_predictoor_rewards(predictoors, tokens_avail)

    # the rewards of each Predictoor should be proportionate to its accuracy
    for address, p in predictoors.items():
        if p.prediction_count < MIN_PREDICTIONS:
            assert rewards.get(address, 0) == 0
            continue
        expected_reward = (
            (p.accuracy / total_accuracy) * tokens_avail if total_accuracy != 0 else 0
        )
        assert (
            abs(rewards.get(address, 0) - expected_reward) < 1e-6
        )  # allow for small floating point differences

    # Sum of all rewards should be equal to tokens available
    assert (
        abs(sum(rewards.values()) - tokens_avail) < 1e-6
    )  # allow for small floating point differences
