import random
from typing import Dict, Union

from df_py.predictoor.calcrewards import calc_predictoor_rewards, filter_predictoors
from df_py.predictoor.models import Predictoor, PredictoorBase
from df_py.util.constants import MIN_PREDICTIONS


def test_filterPredictoors():
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


def test_calcPredictoorRewards_no_predictions():
    predictoors: Dict[str, Union[PredictoorBase, Predictoor]] = {}

    rewards = calc_predictoor_rewards(predictoors, 100)

    assert len(rewards) == 0


def test_calcPredictoorRewards_one_prediction_not_eligible():
    p1 = Predictoor("0x1")
    p1._prediction_count = MIN_PREDICTIONS - 1
    p1._correct_prediction_count = 5
    predictoors = {"0x1": p1}

    rewards = calc_predictoor_rewards(predictoors, 100)

    assert len(rewards) == 0
    assert rewards.get(p1.address, 0) == 0


def test_calcPredictoorRewards_one_prediction_eligible():
    p1 = Predictoor("0x1")
    p1._prediction_count = MIN_PREDICTIONS + 1
    p1._correct_prediction_count = 5
    predictoors = {"0x1": p1}

    rewards = calc_predictoor_rewards(predictoors, 100)

    assert len(rewards) == 1
    assert rewards.get(p1.address, 0) == 100


def test_calcPredictoorRewards_with_predictions():
    p1 = Predictoor("0x1")
    p1._prediction_count = MIN_PREDICTIONS + 100
    p1._correct_prediction_count = 5
    p2 = Predictoor("0x2")
    p2._prediction_count = MIN_PREDICTIONS + 100
    p2._correct_prediction_count = 5
    p3 = Predictoor("0x3")
    p3._prediction_count = MIN_PREDICTIONS - 1
    p3._correct_prediction_count = 2
    predictoors = {"0x1": p1, "0x2": p2, "0x3": p3}

    rewards = calc_predictoor_rewards(predictoors, 100)

    assert len(rewards) == 2
    assert rewards["0x1"] == 50.0
    assert rewards["0x2"] == 50.0


def test_calcPredictoorRewards_fuzz():
    predictoors = {}
    total_accuracy = 0
    for i in range(100):  # generate 100 predictoors
        address = f"0x{i}"
        p = Predictoor(address)
        p._prediction_count = random.randint(
            round(MIN_PREDICTIONS * 0.9), round(MIN_PREDICTIONS * 1.2)
        )
        p._correct_prediction_count = random.randint(0, p._prediction_count)
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
