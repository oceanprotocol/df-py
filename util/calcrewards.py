from typing import Dict, Tuple

from enforce_typing import enforce_types

from util import approvedfilter, cleancase, tousd
from util.tok import TokSet


@enforce_types
def calcRewards(
    stakes: dict,
    poolvols: dict,
    approved_tokens: TokSet,
    rates: Dict[str, float],
    TOKEN_avail: float,
) -> Tuple[Dict[str, Dict[str, float]], Dict[str, Dict[str, Dict[str, float]]]]:
    """
    @arguments
      stakes - dict of [chainID][basetoken_address][pool_addr][LP_addr] : stake
      poolvols -- dict of [chainID][basetoken_address][pool_addr] : vol
      approved_tokens -- TokSet
      rates -- dict of [basetoken_symbol] : USD_per_basetoken
      TOKEN_avail -- float, e.g. amount of OCEAN available

    @return
      rewardsperlp -- dict of [chainID][LP_addr] : TOKEN_float -- reward per chain/LP
      rewardsinfo -- dict of [chainID][pool_addr][LP_addr] : TOKEN_float -- reward per chain/LP

    @notes
      A stake or vol value is denominated in basetoken (eg OCEAN, H2O).
    """
    # ensure upper/lowercase is correct
    (stakes, poolvols, rates) = cleancase.modTuple(stakes, poolvols, rates)

    # remove non-approved tokens
    (stakes, poolvols) = approvedfilter.modTuple(approved_tokens, stakes, poolvols)

    # key params
    TARGET_WPY = 0.015717  # (Weekly Percent Yield) needs to be 1.5717%.
    TARGET_REWARD_AMT = _sumStakes(stakes) * TARGET_WPY
    TOKEN_avail = min(TOKEN_avail, TARGET_REWARD_AMT)  # Max apy is 125%

    # main work
    tok_set = approved_tokens  # use its mapping here, not the 'whether approved' part
    stakes_USD = tousd.stakesToUsd(stakes, rates, tok_set)
    poolvols_USD = tousd.poolvolsToUsd(poolvols, rates, tok_set)
    (rewardsperlp, rewardsinfo) = _calcRewardsUsd(stakes_USD, poolvols_USD, TOKEN_avail)
    return rewardsperlp, rewardsinfo


def _sumStakes(stakes: dict) -> float:
    total_stakes = 0
    for chainID in stakes:
        for basetoken_address in stakes[chainID]:
            for pool_addr in stakes[chainID][basetoken_address]:
                for LP_addr in stakes[chainID][basetoken_address][pool_addr]:
                    total_stakes += stakes[chainID][basetoken_address][pool_addr][
                        LP_addr
                    ]
    return total_stakes


def _calcRewardsUsd(
    stakes_USD: dict, poolvols_USD: Dict[str, Dict[str, float]], TOKEN_avail: float
) -> Tuple[Dict[str, Dict[str, float]], Dict[str, Dict[str, Dict[str, float]]]]:
    """
    @arguments
      stakes_USD - dict of [chainID][pool_addr][LP_addr] : stake_USD
      poolvols_USD -- dict of [chainID][pool_addr] : vol_USD
      TOKEN_avail -- float, e.g. amount of OCEAN available

    @return
      rewardsperlp -- dict of [chainID][LP_addr] : TOKEN_float -- reward per chain/LP
      rewardsinfo -- dict of [chainID][pool_addr][LP_addr] : TOKEN_float -- reward per chain/LP
    """
    cleancase.assertStakesUsd(stakes_USD)
    cleancase.assertPoolvolsUsd(poolvols_USD)

    # base data
    chainIDs = list(stakes_USD.keys())
    pool_addr_set, LP_addr_set = set(), set()
    for chainID in chainIDs:
        pool_addr_set |= set(poolvols_USD[chainID].keys())
        LP_addr_set |= set(
            {addr for addrs in stakes_USD[chainID].values() for addr in addrs}
        )
    pool_addrs, LP_addrs = list(pool_addr_set), list(LP_addr_set)

    # fill in R
    rewardsperlp: dict = {
        cID: {} for cID in chainIDs
    }  # [chainID][LP_addr]:basetoken_float
    rewardsinfo: dict = {}  # [chainID][pool_addr][LP_addr]:basetoken_float

    tot_rewards = 0.0
    for chainID in chainIDs:
        for _, LP_addr in enumerate(LP_addrs):
            reward_i = 0.0
            for _, pool_addr in enumerate(pool_addrs):
                if pool_addr not in stakes_USD[chainID]:
                    continue
                Sij = stakes_USD[chainID][pool_addr].get(LP_addr, 0.0)
                Cj = poolvols_USD[chainID].get(pool_addr, 0.0)
                if Sij == 0 or Cj == 0:
                    continue
                RF_ij = Sij * Cj  # main formula!
                reward_i += RF_ij

                if not chainID in rewardsinfo:
                    rewardsinfo[chainID] = {}
                if not pool_addr in rewardsinfo[chainID]:
                    rewardsinfo[chainID][pool_addr] = {}

                rewardsinfo[chainID][pool_addr][LP_addr] = RF_ij
            if reward_i > 0.0:
                rewardsperlp[chainID][LP_addr] = reward_i
                tot_rewards += reward_i

    # normalize rewards
    for chainID in chainIDs:
        for LP_addr, reward in rewardsperlp[chainID].items():
            rewardsperlp[chainID][LP_addr] = reward / tot_rewards

    # remove small amounts
    for chainID in chainIDs:
        for LP_addr, reward in rewardsperlp[chainID].items():
            if rewardsperlp[chainID][LP_addr] < 0.00001:
                del rewardsperlp[chainID][LP_addr]

    # scale rewards
    for chainID in chainIDs:
        for LP_addr, reward in rewardsperlp[chainID].items():
            rewardsperlp[chainID][LP_addr] = reward * TOKEN_avail

    for chainID in rewardsinfo:
        for pool_addr in rewardsinfo[chainID]:
            for LP_addr, reward in rewardsinfo[chainID][pool_addr].items():
                rewardsinfo[chainID][pool_addr][LP_addr] = (
                    reward / tot_rewards * TOKEN_avail
                )
    # return dict
    return rewardsperlp, rewardsinfo
