from typing import Dict, Tuple

from enforce_typing import enforce_types
import numpy

from util import approvedfilter, cleancase, tousd
from util.tok import TokSet

TARGET_WPY = 0.015717  # (Weekly Percent Yield) needs to be 1.5717%., for max APY of 125%

@enforce_types
def calcRewards(
        stakes: dict,
        poolvols: dict,
        approved_tokens: TokSet,
        rates: Dict[str, float],
        rewards_avail_TOKEN: float,
        rewards_symbol: str,
) -> tuple:
    """
    @arguments
      stakes - dict of [chainID][basetoken_address][pool_addr][LP_addr] : stake_OCEAN_or_H2O
      poolvols -- dict of [chainID][basetoken_address][pool_addr] : vol_OCEAN_or_H2O
      approved_tokens -- TokSet
      rates -- dict of [basetoken_symbol] : USD_per_basetoken
      rewards_avail_TOKEN -- float -- amount of rewards avail, in units of OCEAN or PSDN
      rewards_symbol -- e.g. "OCEAN" or "PSDN"

    @return
      rewardsperlp -- dict of [chainID][LP_addr] : TOKEN_float -- reward per chain/LP
      rewardsinfo -- dict of [chainID][pool_addr][LP_addr] : TOKEN_float -- reward per chain/LP
    """
    (stakes, poolvols, rates) = cleancase.modTuple(stakes, poolvols, rates)
    (stakes, poolvols) = approvedfilter.modTuple(approved_tokens, stakes, poolvols)
    tok_set = approved_tokens  # use its mapping here, not the 'whether approved' part
    
    stakes_USD = tousd.stakesToUsd(stakes, rates, tok_set)
    poolvols_USD = tousd.poolvolsToUsd(poolvols, rates, tok_set)

    rewards_avail_USD = rewards_avail_TOKEN * rates[rewards_symbol]
    
    RF_USD, keys_tup = _calcRewardsUsd(stakes_USD, poolvols_USD, rewards_avail_USD)
    RF_TOKEN = RF_USD / rates[TOKEN_SYMBOL]

    (rewardsperlp, rewardsinfo) = _RF_to_dicts(RF_USD, keys_tup)
    
    return rewardsperlp, rewardsinfo


@enforce_types
def _calcRewardsUsd(stakes_USD: dict, poolvols_USD: dict, rewards_avail_USD: float) -> tuple:
    """
    @arguments
      stakes_USD - dict of [chainID][pool_addr][LP_addr] : stake_USD
      poolvols_USD -- dict of [chainID][pool_addr] : vol_USD
      rewards_avail_USD -- float -- amount of rewards available, in units of USD

    @return
      RF_USD -- 3d array of [chain c, LP i, pool j]; each entry is denominated in USD
      keys_tup -- tuple of (chainIDs list, LP_addrs list, pool_addrs list)
    """
    #base data
    cleancase.assertStakesUsd(stakes_USD)
    cleancase.assertPoolvolsUsd(poolvols_USD)
    chainIDs = list(stakes_USD.keys())
    LP_addrs = _getLpAddrs(stakes_USD)
    pool_addrs = _getPoolAddrs(poolvols_USD)
    N_c, N_i, N_j = len(chainIDs), len(LP_addrs), len(pool_addrs)

    # convert stakes & poolvols to arrays S & P
    S = numpy.zeros((N_c, N_i, N_j), dtype=float)
    P = numpy.zeros((N_c, N_j), dtype=float)
    for c, chainID in enumerate(chainIDs):
        for i, LP_addr in enumerate(LP_addrs):
            for j, pool_addr in enumerate(pool_addrs):
                if pool_addr not in stakes_USD[chainID]:
                    continue
                S[c,i,j] = stakes_USD[chainID][pool_addr].get(LP_addr, 0.0)
                P[c,j] += poolvols_USD[chainID].get(pool_addr, 0.0)

    # compute reward function, store in array RF[c,i,j]
    RF = numpy.zeros((N_c, N_i, N_j), dtype=float)
    for c in range(N_c):
        for i in range(N_i):
            for j in range(N_j):
                RF[c,i,j] = S[c,i,j] * V[c,j] # main formula!

    # normalize values
    RF_norm = RF / numpy.sum(RF)

    # filter negligible values (<0.001% of total RF)
    RF_norm[RF_norm < 0.0001] = 0.0
    RF_norm = RF_norm / numpy.sum(RF_norm)

    # bound APY globally - across all pools
    rewards_avail_USD = min(rewards_avail_USD, numpy.sum(S) * TARGET_WPY)

    # first-cut compute reward per LP
    RF_USD = RF_norm * rewards_avail_USD

    # bound APY at pool level    
    for c in range(N_c):
        for j in range(N_j):
            pool_rewards_avail_USD = min(rewards_avail_USD, numpy.sum(S[c,:,j]) * TARGET_WPY)
            RF_USD[c,:,j]

    # bound APY at LP level

    # compute rewardsperlp -- dict of [chainID][LP_addr] : TOKEN_float -- reward per chain/LP

    # compute rewardsinfo -- dict of [chainID][pool_addr][LP_addr] : TOKEN_float -- reward per chain/LP
    
                


    rewardsperlp: dict = {
        cID: {} for cID in chainIDs
    }  # [chainID][LP_addr]:basetoken_float

                
    # normalize rewards
    for chainID in chainIDs:
        for LP_addr, reward in rewardsperlp[chainID].items():
            rewardsperlp[chainID][LP_addr] = reward / tot_rewards

    # remove small amounts
    for chainID in chainIDs:
        LP_addrs = list(rewardsperlp[chainID].items())
        for LP_addr in LP_addrs:
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


@enforce_types
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



def _RF_to_dicts(RF_TOKEN, keys_tup) -> Tuple[dict, dict]:
    """
    @arguments
      RF_TOKEN -- 3d array of [chain c, LP i, pool j]; each entry is denominated in OCEAN, PSDN, etc
      keys_tup -- tuple of (chainIDs list, LP_addrs list, pool_addrs list)

    @return
      rewardsperlp -- dict of [chainID][LP_addr] : TOKEN_float -- reward per chain/LP
      rewardsinfo -- dict of [chainID][pool_addr][LP_addr] : TOKEN_float -- reward per chain/LP
    """
    chainIDs, LP_addrs, pool_addrs = keys_tup
    
    rewardsperlp, rewardsinfo = {}, {}
    for c, chainID in enumerate(chainIDs):
        for i, LP_addr in enumerate(LP_addrs):
            for j, pool_addr in enumerate(pool_addrs):
                assert RF_TOKEN[c,i,j] >= 0.0
                if RF_TOKEN[c,i,j] == 0.0:
                    continue
                
                if chainID not in rewardsperlp:
                    rewardsperlp[chainID] = {}
                if LP_addr not in rewardsperlp[chainID]:
                    rewardsperlp[chainID][LP_addr] = 0.0
                rewardsperlp[chainID][LP_addr] += RF_TOKEN[c,i,j]

                if chainID not in rewardsinfo:
                    rewardsinfo[chainID] = {}
                if pool_addr not in rewardsinfo[chainID]:
                    rewardsinfo[chainID][pool_addr] = {}
                rewardsinfo[chainID][pool_addr][LP_addr] = RF_TOKEN[c,i,j]

    return rewardsperlp, rewardsinfo
                    

        

@enforce_types
def _getPoolAddrs(poolvols_USD: dict) -> List[str]:
    pool_addr_set = set()
    for chainID in poolvols_USD:
        pool_addr_set |= set(poolvols_USD[chainID].keys())
    return list(pool_addr_set)


@enforce_types
def _getLpAddrs(stakes_USD: dict) -> List[str]:
    LP_addr_set = set()
    for chainID in stakes_USD:
        LP_addr_set |= set(
            {addr for addrs in stakes_USD[chainID].values() for addr in addrs}
        )
    return list(LP_addr_set)
