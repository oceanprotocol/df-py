from unittest.mock import patch

from df_py.challenge.calcrewards import calc_challenge_rewards


def test_calc_challenge_rewards():
    from_addrs = [
        "0xfrom1",
        "0xfrom2",
        "0xfrom3",
    ]

    with patch("df_py.challenge.calcrewards.getrate", return_value=0.5):
        rewards = calc_challenge_rewards(from_addrs, 1000)

    assert len(rewards) == 3
    assert rewards[0]["OCEAN_amt"] == 5000
    assert rewards[1]["OCEAN_amt"] == 3000
    assert rewards[2]["OCEAN_amt"] == 2000
