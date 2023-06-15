from datetime import datetime
from typing import Any, Dict, List

from df_py.util.getrate import getrate


def calc_challenge_rewards(
    from_addrs: list, tokens_avail: float
) -> List[Dict[str, Any]]:
    # TODO: tokens avail??

    rewards = []
    today = datetime.now().strftime("%Y-%m-%d")

    rewards_amts = [2500, 1500, 1000]
    rewards_amts = [
        (1 / getrate("OCEAN", today, today)) * reward_amt for reward_amt in rewards_amts
    ]

    for i in range(3):
        rewards.append(
            {
                "winner_addr": from_addrs[i],
                "OCEAN_amt": rewards_amts[i],
            }
        )

    return rewards
