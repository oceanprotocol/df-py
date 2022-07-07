from typing import Dict, List, Tuple

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
    
    S_USD, P_USD, keys_tup = _stakevolDictsToArrays(stakes_USD, poolvols_USD)
    
    rewards_avail_USD = rewards_avail_TOKEN * rates[rewards_symbol]
    
    RF_USD = _calcRewardsUsd(S_USD, P_USD, rewards_avail_USD)
    
    RF_TOKEN = RF_USD / rates[rewards_symbol]

    (rewardsperlp, rewardsinfo) = _rewardArrayToDicts(RF_TOKEN, keys_tup)
    
    return rewardsperlp, rewardsinfo


def _stakevolDictsToArrays(stakes_USD: dict, poolvols_USD: dict):
    """
    @arguments
      stakes_USD - dict of [chainID][pool_addr][LP_addr] : stake_USD
      poolvols_USD -- dict of [chainID][pool_addr] : vol_USD

    @return
      S_USD -- 3d array of [chain c, LP i, pool j] -- stake for each {c,i,j}, in USD
      P_USD -- 2d array of [chain c, pool j] -- poolvol for each {c,j}, in USD
      keys_tup -- tuple of (chainIDs list, LP_addrs list, pool_addrs list)
    """
    #base data
    cleancase.assertStakesUsd(stakes_USD)
    cleancase.assertPoolvolsUsd(poolvols_USD)
    chainIDs = list(stakes_USD.keys())
    LP_addrs = _getLpAddrs(stakes_USD)
    pool_addrs = _getPoolAddrs(poolvols_USD)
    N_c, N_i, N_j = len(chainIDs), len(LP_addrs), len(pool_addrs)

    #convert
    S_USD = numpy.zeros((N_c, N_i, N_j), dtype=float)
    P_USD = numpy.zeros((N_c, N_j), dtype=float)
    for c, chainID in enumerate(chainIDs):
        for i, LP_addr in enumerate(LP_addrs):
            for j, pool_addr in enumerate(pool_addrs):
                if pool_addr not in stakes_USD[chainID]:
                    continue
                S_USD[c,i,j] = stakes_USD[chainID][pool_addr].get(LP_addr, 0.0)
                P_USD[c,j] += poolvols_USD[chainID].get(pool_addr, 0.0)

    #done!
    keys_tup = (chainIDs, LP_addrs, pool_addrs)
    return S_USD, P_USD, keys_tup


@enforce_types
def _calcRewardsUsd(S_USD, P_USD, rewards_avail_USD: float) -> tuple:
    """
    @arguments
      S_USD -- 3d array of [chain c, LP i, pool j] -- stake for each {c,i,j}, in USD
      P_USD -- 2d array of [chain c, pool j] -- poolvol for each {c,j}, in USD
      rewards_avail_USD -- float -- amount of rewards available, in units of USD

    @return
      RF_USD -- 3d array of [chain c, LP i, pool j]; each entry is denominated in USD
    """
    N_c, N_i, N_j = S_USD.shape

    # compute reward function, store in array RF[c,i,j]
    RF = numpy.zeros((N_c, N_i, N_j), dtype=float)
    for c in range(N_c):
        for i in range(N_i):
            for j in range(N_j):
                RF[c,i,j] = S_USD[c,i,j] * P_USD[c,j] # main formula!

    # normalize values
    RF_norm = RF / numpy.sum(RF)

    # filter negligible values (<0.001% of total RF), then re-normalize
    RF_norm[RF_norm < 0.0001] = 0.0
    RF_norm = RF_norm / numpy.sum(RF_norm)

    # reward in USD
    RF_USD = numpy.zeros((N_c, N_i, N_j), dtype=float)
    for c in range(N_c):
        for i in range(N_i):
            for j in range(N_j):
                RF_USD[c,i,j] = min(RF_norm[c,i,j] * rewards_avail_USD, # baseline
                                    S_USD[c,i,j] * TARGET_WPY)          # APY constraint
                                    
    # done!
    assert not numpy.isnan(numpy.min(RF_USD))
    assert numpy.sum(RF_USD) <= rewards_avail_USD
    return RF_USD


@enforce_types
def _rewardArrayToDicts(RF_TOKEN, keys_tup) -> Tuple[dict, dict]:
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
                assert RF_TOKEN[c,i,j] >= 0.0, RF_TOKEN[c,i,j]
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
