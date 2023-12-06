from datetime import datetime

import pytest
from enforce_typing import enforce_types
from pytest import approx

from df_py.util import networkutil, vesting_schedule
from df_py.util.base18 import from_wei
from df_py.util.constants import ACTIVE_REWARDS_MULTIPLIER, PREDICTOOR_OCEAN_BUDGET


challenge_substream = "challenge"
predictoor_substream = "predictoor"
volume_substream = "volume"
test_params = [
    (datetime(2023, 3, 9), 0),
    (datetime(2023, 3, 16), 150000.0),
    (datetime(2023, 4, 13), 150000.0),
    (datetime(2023, 6, 15), 150000.0),
    (datetime(2024, 3, 7), 150000.0),
    (datetime(2024, 3, 14), 300000),
    (datetime(2024, 9, 5), 300000),
    (datetime(2024, 9, 12), 600000),
    (datetime(2025, 3, 6), 600000),
    (datetime(2025, 3, 13), 1206708.9),
    (datetime(2025, 3, 20), 1206708.9),
    (datetime(2029, 2, 22), 1206708.9),
    (datetime(2029, 3, 1), 1206708.9),
    (datetime(2029, 3, 8), 948128.42),
    (datetime(2029, 3, 15), 603354.452),
    (datetime(2033, 2, 24), 603354.452),
    (datetime(2033, 3, 3), 603354.452),
    (datetime(2033, 3, 10), 344773.972),
    (datetime(2033, 3, 17), 301677.22),
    (datetime(2037, 1, 14), 301677.22),
    (datetime(2037, 2, 26), 301677.226),
    (datetime(2037, 3, 5), 258580.47),
    (datetime(2037, 3, 12), 150838.61),
    (datetime(2041, 2, 21), 150838.61),
    (datetime(2041, 2, 28), 150838.61),
    (datetime(2041, 3, 7), 96967.67),
    (datetime(2041, 3, 14), 75419.30),
    (datetime(2041, 3, 14), 75419.30),
    (datetime(2045, 3, 14), 37709.65),
    # may df-py live long and prosper
]


def test_get_active_reward_amount_for_week_eth_by_stream():
    start_dt = datetime(2022, 1, 1)
    assert (
        vesting_schedule.get_active_reward_amount_for_week_eth_by_stream(
            start_dt, predictoor_substream, networkutil.DEV_CHAINID
        )
        == 0
    )

    start_dt = datetime(2042, 1, 1)
    assert (
        vesting_schedule.get_active_reward_amount_for_week_eth_by_stream(
            start_dt, predictoor_substream, networkutil.DEV_CHAINID
        )
        > 0
    )

    challenge_rewards = (
        vesting_schedule.get_active_reward_amount_for_week_eth_by_stream(
            start_dt, challenge_substream, networkutil.DEV_CHAINID
        )
    )

    predictoor_rewards = (
        vesting_schedule.get_active_reward_amount_for_week_eth_by_stream(
            start_dt, predictoor_substream, networkutil.DEV_CHAINID
        )
    )

    volume_rewards = vesting_schedule.get_active_reward_amount_for_week_eth_by_stream(
        start_dt, volume_substream, networkutil.DEV_CHAINID
    )

    total_rewards = vesting_schedule.get_active_reward_amount_for_week_eth(
        start_dt, networkutil.DEV_CHAINID
    )

    assert total_rewards == approx(
        challenge_rewards + predictoor_rewards + volume_rewards, 0.1
    )

    invalid_substream = "invalid_substream"
    with pytest.raises(ValueError):
        vesting_schedule.get_active_reward_amount_for_week_eth_by_stream(
            start_dt, invalid_substream, networkutil.DEV_CHAINID
        )


def test_launch_dates():
    # a week before predictoor's launch
    start_dt = datetime(2023, 11, 2)
    predictoor_rewards = (
        vesting_schedule.get_active_reward_amount_for_week_eth_by_stream(
            start_dt, predictoor_substream, networkutil.DEV_CHAINID
        )
    )
    assert predictoor_rewards == 0, "Predictoor DF has not begun"

    volume_rewards = vesting_schedule.get_active_reward_amount_for_week_eth_by_stream(
        start_dt, "volume"
    )
    assert volume_rewards == 70000

    challenge_rewards = (
        vesting_schedule.get_active_reward_amount_for_week_eth_by_stream(
            start_dt, challenge_substream, networkutil.DEV_CHAINID
        )
    )
    assert challenge_rewards == 5000

    total_rewards = vesting_schedule.get_active_reward_amount_for_week_eth(start_dt)
    assert total_rewards == predictoor_rewards + volume_rewards + challenge_rewards

    # predictoor's launch
    start_dt = datetime(2023, 11, 9)
    predictoor_rewards = (
        vesting_schedule.get_active_reward_amount_for_week_eth_by_stream(
            start_dt, predictoor_substream, networkutil.DEV_CHAINID
        )
    )

    assert predictoor_rewards == PREDICTOOR_OCEAN_BUDGET

    volume_rewards = vesting_schedule.get_active_reward_amount_for_week_eth_by_stream(
        start_dt, volume_substream, networkutil.DEV_CHAINID
    )
    assert volume_rewards == 37000

    challenge_rewards = (
        vesting_schedule.get_active_reward_amount_for_week_eth_by_stream(
            start_dt, challenge_substream, networkutil.DEV_CHAINID
        )
    )
    assert challenge_rewards == 1000

    total_rewards = vesting_schedule.get_active_reward_amount_for_week_eth(start_dt)
    assert total_rewards == volume_rewards + predictoor_rewards + challenge_rewards


@pytest.mark.parametrize("test_input, expected_output", test_params)
def test_get_reward_amount_for_week_wei(test_input, expected_output):
    assert from_wei(
        vesting_schedule.get_reward_amount_for_week_wei(
            test_input, networkutil.DEV_CHAINID
        )
    ) == approx(expected_output)


@pytest.mark.parametrize("test_input, expected_output", test_params)
def test_get_active_reward_amount_for_week_eth(test_input, expected_output):
    assert vesting_schedule.get_active_reward_amount_for_week_eth(
        test_input, networkutil.DEV_CHAINID
    ) == approx(expected_output * ACTIVE_REWARDS_MULTIPLIER)


@enforce_types
def test_compare_halflife_functions():
    # compare python and solidity halflife function
    value = 503370000 * 1e18
    halflife = 4 * 365 * 24 * 60 * 60  # 4 years
    month = 30 * 24 * 60 * 60

    for i in range(0, int(halflife * 1.5), int(month * 4)):
        py_result = vesting_schedule._halflife(value, i, halflife)
        solidity_result = vesting_schedule._halflife_solidity(
            value, i, halflife, networkutil.DEV_CHAINID
        )
        diff = abs(py_result - solidity_result)
        assert diff < 1e10, f"diff {diff} at i {i/halflife*2}"
