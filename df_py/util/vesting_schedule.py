from datetime import datetime, timedelta

from enforce_typing import enforce_types

from df_py.util import oceanutil
from df_py.util.base18 import from_wei, to_wei
from df_py.util.constants import (
    ACTIVE_REWARDS_MULTIPLIER,
    DFMAIN_CONSTANTS,
    PREDICTOOR_RELEASE_WEEK,
)
from df_py.volume.calcrewards import getDfWeekNumber


@enforce_types
def getActiveRewardAmountForWeekEthByStream(
    start_dt: datetime, substream: str
) -> float:
    """
    Return the reward amount for the week and substream in ETH starting at start_dt.
    This is the amount that will be allocated to active rewards.
    """
    total_reward_amount = getActiveRewardAmountForWeekEth(start_dt)

    dfweek = getDfWeekNumber(start_dt) - 1

    if substream == "predictoor":
        return total_reward_amount * 0.01 if dfweek >= PREDICTOOR_RELEASE_WEEK else 0
    else:
        raise ValueError("Unrecognized substream: {}".format(substream))


@enforce_types
def getActiveRewardAmountForWeekEth(start_dt: datetime) -> float:
    """
    Return the reward amount for the week in ETH starting at start_dt.
    This is the amount that will be allocated to active rewards.
    """
    total_reward_amount = getRewardAmountForWeekWei(start_dt)
    active_reward_amount = int(total_reward_amount * ACTIVE_REWARDS_MULTIPLIER)
    active_reward_amount_eth = from_wei(active_reward_amount)
    return active_reward_amount_eth


@enforce_types
def getRewardAmountForWeekWei(start_dt: datetime) -> int:
    """
    Return the total reward amount for the week in WEI starting at start_dt.
    This amount is in accordance with the vesting schedule.
    Returns 0 if the week is before the start of the vesting schedule (DF29).
    """

    # hardcoded values for linear vesting schedule
    dfweek = getDfWeekNumber(start_dt) - 1

    for start_week, value in DFMAIN_CONSTANTS.items():
        if dfweek < start_week:
            return to_wei(value)

    # halflife
    TOT_SUPPLY = 503370000 * 1e18
    HALF_LIFE = 4 * 365 * 24 * 60 * 60  # 4 years
    end_dt = start_dt + timedelta(days=7)

    vesting_start_dt = datetime(2025, 3, 13)
    vesting_tot_amount = TOT_SUPPLY - 32530000
    reward = _halflife_solidity(
        vesting_tot_amount, (end_dt - vesting_start_dt).total_seconds(), HALF_LIFE
    ) - _halflife_solidity(
        vesting_tot_amount, (start_dt - vesting_start_dt).total_seconds(), HALF_LIFE
    )
    return int(reward)


@enforce_types
def _halflife(value, t, h) -> int:
    """
    Approximation of halflife function
    """
    t = int(t)
    h = int(h)
    value = int(value)
    p = value >> int(t // h)
    t %= h
    return int(value - p + (p * t) // h // 2)


@enforce_types
def _halflife_solidity(value, t, h) -> int:
    """
    Halflife function in Solidity, requires network connection and
    deployed VestingWallet contract
    """
    return oceanutil.VestingWalletV0().getAmount(value, t, h)
