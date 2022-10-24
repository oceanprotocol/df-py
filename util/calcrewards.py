from typing import Dict, List, Tuple

from enforce_typing import enforce_types
import numpy as np

from util import cleancase, tousd

TARGET_WPY = (
    0.015717  # (Weekly Percent Yield) needs to be 1.5717%., for max APY of 125%
)


@enforce_types
def calcRewards(
    allocations: Dict[str, Dict[str, Dict[str, float]]],
    veBalances: Dict[str, float],
    nftvols: Dict[int, Dict[str, Dict[str, float]]],
    symbols: Dict[int, Dict[str, str]],
    rates: Dict[str, float],
    rewards_avail_TOKEN: float,
    rewards_symbol: str,
) -> Tuple[Dict[int, Dict[str, float]], Dict[int, Dict[str, Dict[str, float]]]]:
    """
    @arguments
      allocations - dict of [chainID][nft_addr][LP_addr] : allocation percentage for the user
      veBalances - dict of [LP_addr] : ve balance for the user
      nftvols -- dict of [chainID][basetoken_addr][nft_addr] : data consume volume
      symbols -- dict of [chainID][basetoken_addr] : basetoken_symbol
      rates -- dict of [basetoken_symbol] : USD_price
      rewards_avail_TOKEN -- float -- amount of rewards avail, in units of OCEAN or PSDN
      rewards_symbol -- e.g. "OCEAN" or "PSDN"

    @return
      rewardsperlp -- dict of [chainID][LP_addr] : TOKEN_float -- reward per chain/LP
      rewardsinfo -- dict of [chainID][nft_addr][LP_addr] : TOKEN_float -- reward per chain/LP
    """

    if len(allocations) == 0:
        raise ValueError("No allocations provided")

    if len(veBalances) == 0:
        raise ValueError("No veBalances provided")

    (allocations, nftvols, rates) = cleancase.modTuple(allocations, nftvols, rates)

    nftvols_USD = tousd.nftvolsToUsd(nftvols, symbols, rates)

    veBalances_USD = _veStakesUSD(veBalances, rates["OCEAN"])
    veStakes = _getveStakes(allocations, veBalances_USD)

    S_USD, P_USD, keys_tup = _stakevolDictsToArrays(veStakes, nftvols_USD)
    rewards_avail_USD = rewards_avail_TOKEN * rates[rewards_symbol]

    RF_USD = _calcRewardsUsd(S_USD, P_USD, rewards_avail_USD)
    RF_TOKEN = RF_USD / rates[rewards_symbol]

    (rewardsperlp, rewardsinfo) = _rewardArrayToDicts(RF_TOKEN, keys_tup)

    return rewardsperlp, rewardsinfo


def _veStakesUSD(veBalances: dict, rate: float) -> dict:
    """
    @arguments
      veBalances - dict of [LP_addr] : ve balance for the user
    """
    veStakesUSD = {}
    for LP_addr in veBalances:
        veStakesUSD[LP_addr] = veBalances[LP_addr] * rate
    return veStakesUSD


def _getveStakes(allocations: dict, veBalances: dict) -> dict:
    """
    @arguments
      allocations - dict of [chainID][nft_addr][LP_addr] : allocation percentage for the user
      veBalances - dict of [LP_addr] : ve balance for the user
    """
    VE_stakes: dict = {}
    for chainID in allocations:
        if chainID not in VE_stakes:
            VE_stakes[chainID] = {}
        for nft_addr in allocations[chainID]:
            if nft_addr not in VE_stakes[chainID]:
                VE_stakes[chainID][nft_addr] = {}
            for LP_addr in allocations[chainID][nft_addr]:

                if LP_addr not in veBalances:
                    continue

                allocation = allocations[chainID][nft_addr][LP_addr]
                veBalance = veBalances[LP_addr]
                VE_stakes[chainID][nft_addr][LP_addr] = allocation * veBalance

    return VE_stakes


def _stakevolDictsToArrays(veStakes: dict, nftvols_USD: dict):
    """
    @arguments
      veStakes - dict of [chainID][nft_addr][LP_addr] : stake_USD
      nftvols_USD -- dict of [chainID][nft_addr] : vol_USD

    @return
      S_USD -- 3d array of [chain c, LP i, nft j] -- stake for each {c,i,j}, in USD
      P_USD -- 2d array of [chain c, nft j] -- nftvol for each {c,j}, in USD
      keys_tup -- tuple of (chainIDs list, LP_addrs list, nft_addrs list)
    """
    # base data
    cleancase.assertStakesUsd(veStakes)
    cleancase.assertNFTvolUsd(nftvols_USD)
    chainIDs = list(veStakes.keys())
    LP_addrs = _getLpAddrs(veStakes)
    nft_addrs = _getNftAddrs(nftvols_USD)
    N_c, N_i, N_j = len(chainIDs), len(LP_addrs), len(nft_addrs)

    # convert
    S_USD = np.zeros((N_c, N_i, N_j), dtype=float)
    P_USD = np.zeros((N_c, N_j), dtype=float)

    for c, chainID in enumerate(chainIDs):
        for i, LP_addr in enumerate(LP_addrs):
            for j, nft_addr in enumerate(nft_addrs):
                if nft_addr not in veStakes[chainID]:
                    continue
                S_USD[c, i, j] = veStakes[chainID][nft_addr].get(LP_addr, 0.0)
                P_USD[c, j] += nftvols_USD[chainID].get(nft_addr, 0.0)

    # done!
    keys_tup = (chainIDs, LP_addrs, nft_addrs)

    return S_USD, P_USD, keys_tup


@enforce_types
def _calcRewardsUsd(S_USD, P_USD, rewards_avail_USD: float) -> np.ndarray:
    """
    @arguments
      S_USD -- 3d array of [chain c, LP i, nft j] -- stake for each {c,i,j}, in USD
      P_USD -- 2d array of [chain c, nft j] -- nftvol for each {c,j}, in USD
      rewards_avail_USD -- float -- amount of rewards available, in units of USD

    @return
      RF_USD -- 3d array of [chain c, LP i, nft j] -- rewards denominated in USD
    """
    N_c, N_i, N_j = S_USD.shape

    # compute reward function, store in array RF[c,i,j]
    RF = np.zeros((N_c, N_i, N_j), dtype=float)
    for c in range(N_c):
        for i in range(N_i):
            for j in range(N_j):
                RF[c, i, j] = S_USD[c, i, j] * P_USD[c, j]  # main formula!

    if np.sum(RF) == 0.0:
        return np.zeros((N_c, N_i, N_j), dtype=float)

    # normalize values
    RF_norm = RF / np.sum(RF)

    # filter negligible values (<0.00001% of total RF), then re-normalize
    RF_norm[RF_norm < 0.000001] = 0.0

    if np.sum(RF_norm) == 0.0:
        return np.zeros((N_c, N_i, N_j), dtype=float)

    RF_norm = RF_norm / np.sum(RF_norm)

    # reward in USD
    RF_USD = np.zeros((N_c, N_i, N_j), dtype=float)
    for c in range(N_c):
        for i in range(N_i):
            for j in range(N_j):
                RF_USD[c, i, j] = min(
                    RF_norm[c, i, j] * rewards_avail_USD,  # baseline
                    S_USD[c, i, j] * TARGET_WPY,  # APY constraint
                )
    # postcondition: nans
    assert not np.isnan(np.min(RF_USD)), RF_USD

    # postcondition: sum is ok. First check within a tol; shrink slightly if needed
    sum1 = np.sum(RF_USD)
    tol = 1e-13
    assert sum1 <= rewards_avail_USD * (1 + tol), (sum1, rewards_avail_USD, RF_USD)
    if sum1 > rewards_avail_USD:
        RF_USD /= 1 + tol
    sum2 = np.sum(RF_USD)
    assert sum1 <= rewards_avail_USD * (1 + tol), (sum2, rewards_avail_USD, RF_USD)

    # done!
    return RF_USD


@enforce_types
def _rewardArrayToDicts(RF_TOKEN, keys_tup) -> Tuple[dict, dict]:
    """
    @arguments
      RF_TOKEN -- 3d array of [chain c, LP i, nft j]; each entry is denominated in OCEAN, PSDN, etc
      keys_tup -- tuple of (chainIDs list, LP_addrs list, nft_addrs list)

    @return
      rewardsperlp -- dict of [chainID][LP_addr] : TOKEN_float -- reward per chain/LP
      rewardsinfo -- dict of [chainID][nft_addr][LP_addr] : TOKEN_float -- reward per chain/LP
    """
    chainIDs, LP_addrs, nft_addrs = keys_tup

    rewardsperlp: dict = {}
    rewardsinfo: dict = {}
    for c, chainID in enumerate(chainIDs):
        for i, LP_addr in enumerate(LP_addrs):
            for j, nft_addr in enumerate(nft_addrs):
                assert RF_TOKEN[c, i, j] >= 0.0, RF_TOKEN[c, i, j]
                if RF_TOKEN[c, i, j] == 0.0:
                    continue

                if chainID not in rewardsperlp:
                    rewardsperlp[chainID] = {}
                if LP_addr not in rewardsperlp[chainID]:
                    rewardsperlp[chainID][LP_addr] = 0.0
                rewardsperlp[chainID][LP_addr] += RF_TOKEN[c, i, j]

                if chainID not in rewardsinfo:
                    rewardsinfo[chainID] = {}
                if nft_addr not in rewardsinfo[chainID]:
                    rewardsinfo[chainID][nft_addr] = {}
                rewardsinfo[chainID][nft_addr][LP_addr] = RF_TOKEN[c, i, j]

    return rewardsperlp, rewardsinfo


@enforce_types
def _getNftAddrs(nftvols_USD: dict) -> List[str]:
    nft_addr_set = set()
    for chainID in nftvols_USD:
        nft_addr_set |= set(nftvols_USD[chainID].keys())
    return list(nft_addr_set)


@enforce_types
def _getLpAddrs(stakes_USD: dict) -> List[str]:
    LP_addr_set = set()
    for chainID in stakes_USD:
        for nft_addr in stakes_USD[chainID]:
            LP_addr_set |= set(stakes_USD[chainID][nft_addr].keys())
    return list(LP_addr_set)
