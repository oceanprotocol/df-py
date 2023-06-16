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
    today = today.strftime("%Y-%m-%d")

    return [
        (1 / getrate("OCEAN", today, today)) * reward_amt
        for reward_amt in rewards_in_usdt
    ]


def calc_challenge_rewards(
    from_addrs: list, tokens_avail: float
) -> List[Dict[str, Any]]:
    """Returns a dict of rewards for the challenge, each entry having keys:
    - winner_addr: ethereum address of the winner
    - OCEAN_amt: number of OCEAN tokens to award the winner

    :param from_addrs: list of Ethereum addresses
    :param tokens_avail: number of tokens available for rewards
    :return: list of dicts
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
