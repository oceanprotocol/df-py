from enforce_typing import enforce_types
from typing import Dict, Set, Tuple
from numpy import log10


@enforce_types
def calcRewards(
    stakes: dict, pool_vols: dict, rates: Dict[str, float], OCEAN_avail: float
) -> Dict[str, float]:
    """
    @arguments
      stakes - dict of [chainID][basetoken_symbol][pool_addr][LP_addr] : stake
      pool_vols -- dict of [chainID][basetoken_symbol][pool_addr] : vol
      rates -- dict of [basetoken_symbol] : USD_per_basetoken
      OCEAN_avail -- float

    @return
      rewards -- dict of [chainID][LP_addr] : OCEAN_float

    A stake or vol value is denominated in basetoken (eg OCEAN, H2O).
    """
    stakes_USD = _stakesToUsd(stakes, rates)
    pool_vols_USD = _poolVolsToUsd(pool_vols, rates)
    rewards = _calcRewardsUsd(stakes_USD, pool_vols_USD, OCEAN_avail)
    return rewards


def _stakesToUsd(stakes: dict, rates: Dict[str, float]) -> dict:
    """
    @description
      Converts stake values to be USD-denominated.

    @arguments
      stakes - dict of [chainID][basetoken_symbol][pool_addr][LP_addr] : stake
      rates -- dict of [basetoken_symbol] : USD_per_basetoken

    @return
      stakes_USD -- dict of [chainID][pool_addr][LP_addr] : stake_USD
    """
    stakes_USD = {}
    for chainID in stakes:
        stakes_USD[chainID] = _stakesToUsdAtChain(stakes[chainID], rates)
    return stakes_USD

def _stakesToUsdAtChain(stakes_at_chain: dict, rates: Dict[str, float]) -> dict:
    """Like stakesToUsd, but at a single chainID"""
    stakes_USD_at_chain = {}
    for basetoken, rate in rates.items():
        if basetoken not in stakes_at_chain:
            continue
        for pool_addr in stakes_at_chain[basetoken].keys():
            stakes_USD_at_chain[pool_addr] = {}
            for LP_addr, stake in stakes_at_chain[basetoken][pool_addr].items():
                stakes_USD_at_chain[pool_addr][LP_addr] = stake * rate
    return stakes_USD_at_chain


def _poolVolsToUsd(pool_vols: dict, rates: Dict[str, float]) -> Dict[str, float]:
    """
    @description
      For a given chain, converts volume values to be USD-denominated.

    @arguments
      pool_vols -- dict of [chainID][basetoken_symbol][pool_addr] : vol
      rates -- dict of [basetoken_symbol] : USD_per_basetoken

    @return
      pool_vols_USD -- dict of [chainID][pool_addr] : vol_USD
    """
    pool_vols_USD = {}
    for chainID in pool_vols:
        pool_vols_USD[chainID] = _poolVolsToUsdAtChain(pool_vols[chainID], rates)
    return pool_vols_USD

def _poolVolsToUsdAtChain(pool_vols_at_chain: dict, rates: Dict[str, float]) -> Dict[str, float]:
    """Like _poolVolsToUSD, but at a given chainID"""
    pool_vols_USD_at_chain = {}  # dict of [pool_addr] : vol_USD
    for basetoken, rate in rates.items():
        if basetoken not in pool_vols_at_chain:
            continue
        for pool_addr, vol in pool_vols_at_chain[basetoken].items():
            pool_vols_USD_at_chain[pool_addr] = vol * rate

    return pool_vols_USD_at_chain


def _calcRewardsUsd(
    stakes_USD: dict, pool_vols_USD: Dict[str, float], basetoken_avail: float
) -> Dict[str, float]:
    """
    @arguments
      stakes_USD - dict of [chainID][pool_addr][LP_addr] : stake_USD
      pool_vols_USD -- dict of [chainID][pool_addr] : vol_USD
      basetoken_avail -- float, e.g. amount of OCEAN available

    @return
      rewards -- dict of [chainID][LP_addr] : basetoken_float
    """
    # base data
    chainIDs = list(stakes_USD.keys())
    pool_addr_set, LP_addr_set = set(), set()
    for chainID in chainIDs:
        pool_addr_set |= set(pool_vols_USD[chainID].keys())
        LP_addr_set |= set({addr for addrs in stakes_USD[chainID].values()
                            for addr in addrs})
    pool_addrs, LP_addrs = list(pool_addr_set), list(LP_addr_set)

    # fill in R
    rewards_across_chains = {} # [LP_addr]:basetoken_float
    for i, LP_addr in enumerate(LP_addrs):
        reward_i = 0.0
        for j, pool_addr in enumerate(pool_addrs):
            for chainID in chainIDs:
                if pool_addr not in stakes_USD[chainID]:
                    continue
                Sij = stakes_USD[chainID][pool_addr].get(LP_addr, 0.0)
                Cj = pool_vols_USD[chainID].get(pool_addr, 0.0)
                if Sij == 0 or Cj == 0:
                    continue
                RF_ij = log10(Sij + 1.0) * log10(Cj + 2.0)  # main formula!
                reward_i += RF_ij
        if reward_i > 0.0:
            rewards_across_chains[LP_addr] = reward_i

    # normalize and scale rewards
    sum_ = sum(rewards_across_chains.values())
    for LP_addr, reward in rewards.items():
        rewards_across_chains[LP_addr] = reward / sum_ * basetoken_avail

    #FIXME: need to figure out how to put reward on each given chain
    # (won't be trivial!)

    # return dict
    return rewards
