from typing import Dict, Tuple

from enforce_typing import enforce_types
from numpy import log10

from util import cleancase
from util.query import _symbol
from util import networkutil


@enforce_types
def calcRewards(
    stakes: dict, poolvols: dict, rates: Dict[str, float], TOKEN_avail: float
) -> Tuple[Dict[str, Dict[str, float]], Dict[str, Dict[str, Dict[str, float]]]]:
    """
    @arguments
      stakes - dict of [chainID][basetoken_symbol][pool_addr][LP_addr] : stake
      poolvols -- dict of [chainID][basetoken_symbol][pool_addr] : vol
      rates -- dict of [basetoken_symbol] : USD_per_basetoken
      TOKEN_avail -- float, e.g. amount of OCEAN available

    @return
      rewardsperlp -- dict of [chainID][LP_addr] : TOKEN_float -- reward per chain/LP
      rewardsinfo -- dict of [chainID][pool_addr][LP_addr] : TOKEN_float -- reward per chain/LP

    @notes
      A stake or vol value is denominated in basetoken (eg OCEAN, H2O).
    """
    # get cases happy
    stakes = cleancase.modStakes(stakes)
    poolvols = cleancase.modPoolvols(poolvols)
    rates = cleancase.modRates(rates)

    #
    stakes_USD = _stakesToUsd(stakes, rates)
    poolvols_USD = _poolvolsToUsd(poolvols, rates)
    (rewardsperlp, rewardsinfo) = _calcRewardsUsd(stakes_USD, poolvols_USD, TOKEN_avail)
    return rewardsperlp, rewardsinfo


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
    cleancase.assertStakes(stakes)
    cleancase.assertRates(rates)

    stakes_USD = {}
    for chainID in stakes:
        networkutil.connect(chainID)
        stakes_USD[chainID] = _stakesToUsdAtChain(stakes[chainID], rates)

    return stakes_USD


def _stakesToUsdAtChain(stakes_at_chain: dict, rates: Dict[str, float]) -> dict:
    """
    @description
      For a chain, converts stake values to be USD-denominated.

    @arguments
      stakes_at_chain - dict of [basetoken_symbol][pool_addr][LP_addr] : stake
      rates -- dict of [basetoken_symbol] : USD_per_basetoken

    @return
      stakes_USD_at_chain -- dict of [pool_addr][LP_addr] : stake_USD
    """
    cleancase.assertStakesAtChain(stakes_at_chain)
    cleancase.assertRates(rates)

    stakes_USD_at_chain: Dict[str, Dict[str, float]] = {}
    symb_to_addr = {}
    for addr in stakes_at_chain.keys():
        symb = _symbol(addr)
        symb_to_addr[symb] = addr

    for basetoken, rate in rates.items():
        if basetoken not in symb_to_addr.keys():
            continue

        baseaddr = symb_to_addr[basetoken]
        for pool_addr in stakes_at_chain[baseaddr].keys():
            stakes_USD_at_chain[pool_addr] = {}
            for LP_addr, stake in stakes_at_chain[baseaddr][pool_addr].items():
                stakes_USD_at_chain[pool_addr][LP_addr] = stake * rate

    cleancase.assertStakesUsdAtChain(stakes_USD_at_chain)
    return stakes_USD_at_chain


def _poolvolsToUsd(
    poolvols: dict, rates: Dict[str, float]
) -> Dict[str, Dict[str, float]]:
    """
    @description
      For a given chain, converts volume values to be USD-denominated.

    @arguments
      poolvols -- dict of [chainID][basetoken_symbol][pool_addr] : vol
      rates -- dict of [basetoken_symbol] : USD_per_basetoken

    @return
      poolvols_USD -- dict of [chainID][pool_addr] : vol_USD
    """
    cleancase.assertPoolvols(poolvols)
    cleancase.assertRates(rates)

    poolvols_USD = {}
    for chainID in poolvols:
        networkutil.connect(chainID)
        poolvols_USD[chainID] = _poolvolsToUsdAtChain(poolvols[chainID], rates)

    cleancase.assertPoolvolsUsd(poolvols_USD)
    return poolvols_USD


def _poolvolsToUsdAtChain(
    poolvols_at_chain: dict, rates: Dict[str, float]
) -> Dict[str, float]:
    """Like _poolvolsToUsd, but at a given chainID"""
    cleancase.assertPoolvolsAtChain(poolvols_at_chain)
    cleancase.assertRates(rates)

    poolvols_USD_at_chain = {}  # dict of [pool_addr] : vol_USD

    symb_to_addr = {}
    for addr in poolvols_at_chain.keys():
        symb = _symbol(addr)
        symb_to_addr[symb] = addr

    for basetoken, rate in rates.items():
        if basetoken not in symb_to_addr.keys():
            continue
        baseaddr = symb_to_addr[basetoken]
        for pool_addr, vol in poolvols_at_chain[baseaddr].items():
            poolvols_USD_at_chain[pool_addr] = vol * rate

    cleancase.assertPoolvolsUsdAtChain(poolvols_USD_at_chain)
    return poolvols_USD_at_chain


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
    rewardsperlp: Dict[str, Dict[str, float]] = {
        cID: {} for cID in chainIDs
    }  # [chainID][LP_addr]:basetoken_float
    rewardsinfo: Dict[
        str, Dict[str, Dict[str, float]]
    ] = {}  # [chainID][pool_addr][LP_addr]:basetoken_float

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
                RF_ij = log10(Sij + 1.0) * log10(Cj + 2.0)  # main formula!
                reward_i += RF_ij

                if not chainID in rewardsinfo:
                    rewardsinfo[chainID] = {}
                if not pool_addr in rewardsinfo[chainID]:
                    rewardsinfo[chainID][pool_addr] = {}

                rewardsinfo[chainID][pool_addr][LP_addr] = RF_ij
            if reward_i > 0.0:
                rewardsperlp[chainID][LP_addr] = reward_i
                tot_rewards += reward_i

    # normalize and scale rewards
    for chainID in chainIDs:
        for LP_addr, reward in rewardsperlp[chainID].items():
            rewardsperlp[chainID][LP_addr] = reward / tot_rewards * TOKEN_avail

    for chainID in rewardsinfo:
        for pool_addr in rewardsinfo[chainID]:
            for LP_addr, reward in rewardsinfo[chainID][pool_addr].items():
                rewardsinfo[chainID][pool_addr][LP_addr] = (
                    reward / tot_rewards * TOKEN_avail
                )
    # return dict
    return rewardsperlp, rewardsinfo
