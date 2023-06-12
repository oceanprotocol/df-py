from datetime import datetime

import pytest
from enforce_typing import enforce_types
from pytest import approx

from df_py.util import networkutil
from df_py.util.base18 import from_wei
from df_py.util.constants import ACTIVE_REWARDS_MULTIPLIER
from df_py.util import vesting_schedule

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


def test_getActiveRewardAmountForWeekEthByStream():
    predictoor_substream = "predictoor"
    volume_substream = "volume"
    start_dt = datetime(2022, 1, 1)
    assert (
        vesting_schedule.getActiveRewardAmountForWeekEthByStream(
            start_dt, predictoor_substream
        )
        == 0
    )

    start_dt = datetime(2042, 1, 1)
    assert (
        vesting_schedule.getActiveRewardAmountForWeekEthByStream(
            start_dt, predictoor_substream
        )
        > 0
    )

    predictoor_rewards = vesting_schedule.getActiveRewardAmountForWeekEthByStream(
        start_dt, predictoor_substream
    )
    volume_rewards = vesting_schedule.getActiveRewardAmountForWeekEthByStream(
        start_dt, volume_substream
    )
    total_rewards = vesting_schedule.getActiveRewardAmountForWeekEth(start_dt)
    assert total_rewards == predictoor_rewards + volume_rewards

    predictoor_substream = "invalid_substream"
    with pytest.raises(ValueError):
        vesting_schedule.getActiveRewardAmountForWeekEthByStream(
            start_dt, predictoor_substream
        )


@pytest.mark.parametrize("test_input, expected_output", test_params)
def test_getRewardAmountForWeekWei(test_input, expected_output):
    networkutil.connectDev()
    assert from_wei(vesting_schedule.getRewardAmountForWeekWei(test_input)) == approx(
        expected_output
    )


@pytest.mark.parametrize("test_input, expected_output", test_params)
def test_getActiveRewardAmountForWeekEth(test_input, expected_output):
    networkutil.connectDev()
    assert vesting_schedule.getActiveRewardAmountForWeekEth(test_input) == approx(
        expected_output * ACTIVE_REWARDS_MULTIPLIER
    )


@enforce_types
def test_compareHalflifeFunctions():
    # compare python and solidity halflife function
    VALUE = 503370000 * 1e18
    HALF_LIFE = 4 * 365 * 24 * 60 * 60  # 4 years
    MONTH = 30 * 24 * 60 * 60
    for i in range(0, int(HALF_LIFE * 1.5), int(MONTH * 4)):
        py_result = vesting_schedule._halflife(VALUE, i, HALF_LIFE)
        solidity_result = vesting_schedule._halflife_solidity(VALUE, i, HALF_LIFE)
        diff = abs(py_result - solidity_result)
        assert diff < 1e10, f"diff {diff} at i {i/HALF_LIFE*2}"

@enforce_types
def setup_function():
    networkutil.connectDev()

@enforce_types
def teardown_function():
    networkutil.disconnect()
