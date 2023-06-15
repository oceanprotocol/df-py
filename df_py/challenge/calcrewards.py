from datetime import datetime
from typing import Any, Dict, List

from df_py.util.getrate import getrate


REWARDS_AMTS = [2500, 1500, 1000]


def get_challenge_reward_amounts_in_ocean():
    today = datetime.now().strftime("%Y-%m-%d")

    return [
        (1 / getrate("OCEAN", today, today)) * reward_amt for reward_amt in REWARDS_AMTS
    ]


def calc_challenge_rewards(
    from_addrs: list, tokens_avail: float
) -> List[Dict[str, Any]]:
    rewards = []
    rewards_amts = get_challenge_reward_amounts_in_ocean()

    if sum(rewards_amts) > tokens_avail:
        raise ValueError(
            f"Total reward amount {sum(rewards_amts)} is greater than tokens avail {tokens_avail}"
        )

    for i in range(3):
        rewards.append(
            {
                "winner_addr": from_addrs[i],
                "OCEAN_amt": rewards_amts[i],
            }
        )

    return rewards
