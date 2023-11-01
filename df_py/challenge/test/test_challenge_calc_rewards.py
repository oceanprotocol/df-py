from datetime import datetime
from unittest.mock import patch

from df_py.challenge.calc_rewards import calc_challenge_rewards


@patch("df_py.challenge.calc_rewards.CHALLENGE_FIRST_DATE", datetime(2021, 1, 1))
def test_calc_challenge_rewards():
    from_addrs = [
        "0xfrom1",
        "0xfrom2",
        "0xfrom3",
    ]

    rewards = calc_challenge_rewards(from_addrs)

    assert len(rewards) == 3
    assert rewards[0]["OCEAN_amt"] == 2500
    assert rewards[1]["OCEAN_amt"] == 1500
    assert rewards[2]["OCEAN_amt"] == 1000


@patch("df_py.challenge.calc_rewards.CHALLENGE_FIRST_DATE", datetime(2021, 1, 1))
def test_calc_challenge_rewards_with_dates():
    from_addrs = [
        "0xfrom1",
        "0xfrom2",
        "0xfrom3",
    ]

    before_challenge = datetime(2020, 12, 31)
    rewards = calc_challenge_rewards(from_addrs, at_date=before_challenge)

    assert len(rewards) == 3
    assert rewards[0]["OCEAN_amt"] == 0
    assert rewards[1]["OCEAN_amt"] == 0
    assert rewards[2]["OCEAN_amt"] == 0

def test_calc_challenge_rewards_one_day_before_predictoor():
    from_addrs = [
        "0xfrom1",
        "0xfrom2",
        "0xfrom3",
    ]

    pre_predictoor = datetime(2023, 11, 15)
    rewards = calc_challenge_rewards(from_addrs, at_date=pre_predictoor)

    assert len(rewards) == 3
    assert rewards[0]["OCEAN_amt"] == 2500
    assert rewards[1]["OCEAN_amt"] == 1500
    assert rewards[2]["OCEAN_amt"] == 1000

def test_calc_challenge_rewards_predictoor_launch():
    from_addrs = [
        "0xfrom1",
        "0xfrom2",
        "0xfrom3",
    ]

    post_predictoor = datetime(2023, 11, 15)
    rewards = calc_challenge_rewards(from_addrs, at_date=post_predictoor)

    assert len(rewards) == 3
    assert rewards[0]["OCEAN_amt"] == 500
    assert rewards[1]["OCEAN_amt"] == 300
    assert rewards[2]["OCEAN_amt"] == 200
