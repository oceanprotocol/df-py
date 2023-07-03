from datetime import datetime
from typing import Any, Dict, List, Optional

from enforce_typing import enforce_types

from df_py.util.constants import CHALLENGE_FIRST_DATE


@enforce_types
def get_challenge_reward_amounts_in_ocean(
    at_date: Optional[datetime] = None,
) -> List[int]:
    """
    @return
      rewards - list of OCEAN amounts, in order of 1st, 2nd, 3rd place
    """
    today = at_date if at_date else datetime.now()

    if today < CHALLENGE_FIRST_DATE:
        return [0, 0, 0]

    return [2500, 1500, 1000]


@enforce_types
def calc_challenge_rewards(
    from_addrs: list, at_date: Optional[datetime] = None
) -> List[Dict[str, Any]]:
    """Returns a dict of rewards for the challenge.
    @arguments
      - from_addrs: A list of addresses participating in the challenge.
    @return
    rewards -- dict of [winner_address] : float
        The calculated rewards for each winner.
    """
    rewards = []
    rewards_amts = get_challenge_reward_amounts_in_ocean(at_date)

    for i, reward_amt in enumerate(rewards_amts):
        rewards.append(
            {
                "winner_addr": from_addrs[i],
                "OCEAN_amt": reward_amt,
            }
        )

    return rewards
