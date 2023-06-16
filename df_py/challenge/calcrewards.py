from datetime import datetime
from typing import Any, Dict, List

from df_py.util.constants import CHALLENGE_FIRST_DATE
from df_py.util.getrate import getrate


def get_challenge_reward_amounts_in_usdt() -> List[int]:
    """
    @return
      list of USDT amounts, in order of 1st, 2nd, 3rd place
    """
    today = datetime.now()

    if today < CHALLENGE_FIRST_DATE:
        return [0, 0, 0]

    return [625, 375, 250]


def get_challenge_reward_amounts_in_ocean() -> List[int]:
    """
    @return
      rewards - list of OCEAN amounts, in order of 1st, 2nd, 3rd place
    """
    rewards_in_usdt = get_challenge_reward_amounts_in_usdt()

    today = datetime.now()
    today_str = today.strftime("%Y-%m-%d")

    return [
        (1 / getrate("OCEAN", today_str, today_str)) * reward_amt
        for reward_amt in rewards_in_usdt
    ]


def calc_challenge_rewards(
    from_addrs: list, tokens_avail: float
) -> List[Dict[str, Any]]:
    """Returns a dict of rewards for the challenge.
    @arguments
      - from_addrs: A list of addresses participating in the challenge.
      - tokens_avail: The total number of tokens available for rewards.
    @return
      - A list of dictionaries representing rewards for the challenge.
        Each dictionary contains the following keys:
        - winner_addr: The address of the challenge winner.
        - OCEAN_amt: The number of OCEAN tokens to be awarded to the winner.
    """
    rewards = []
    rewards_amts = get_challenge_reward_amounts_in_ocean()

    if sum(rewards_amts) > tokens_avail:
        raise ValueError(
            f"Total reward amount {sum(rewards_amts)} is greater than tokens avail {tokens_avail}"
        )

    for i in range(len(get_challenge_reward_amounts_in_usdt())):
        rewards.append(
            {
                "winner_addr": from_addrs[i],
                "OCEAN_amt": rewards_amts[i],
            }
        )

    return rewards
