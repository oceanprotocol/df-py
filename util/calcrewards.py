from typing import Dict, List, Tuple

from enforce_typing import enforce_types
import numpy as np

from util import cleancase, tousd

# Weekly Percent Yield needs to be 1.5717%., for max APY of 125%
TARGET_WPY = 0.015717


@enforce_types
def calcRewards(
    stakes: Dict[str, Dict[str, Dict[str, float]]],
    nftvols: Dict[int, Dict[str, Dict[str, float]]],
    symbols: Dict[int, Dict[str, str]],
    rates: Dict[str, float],
    rewards_avail: float,
) -> Tuple[Dict[int, Dict[str, float]], Dict[int, Dict[str, Dict[str, float]]]]:
    """
    @arguments
      stakes - dict of [chainID][nft_addr][LP_addr] : veOCEAN_float
      nftvols -- dict of [chainID][basetoken_addr][nft_addr] : consume_volume_float
      symbols -- dict of [chainID][basetoken_addr] : basetoken_symbol_str
      rates -- dict of [basetoken_symbol] : USD_price_float
      rewards_avail -- float -- amount of rewards avail, in units of OCEAN

    @return
      rewardsperlp -- dict of [chainID][LP_addr] : OCEAN_float
      rewardsinfo -- dict of [chainID][nft_addr][LP_addr] : OCEAN_float
    """    
    (stakes, nftvols, rates) = cleancase.modTuple(stakes, nftvols, rates)

    nftvols_USD = tousd.nftvolsToUsd(nftvols, symbols, rates)

    S, V_USD, keys_tup = _stakevolDictsToArrays(stakes, nftvols_USD)

    R = _calcRewardsUsd(S, V_USD, rewards_avail)

    (rewardsperlp, rewardsinfo) = _rewardArrayToDicts(R, keys_tup)

    return rewardsperlp, rewardsinfo


def _stakevolDictsToArrays(stakes: dict, nftvols_USD: dict):
    """
    @arguments
      stakes - dict of [chainID][nft_addr][LP_addr] : veOCEAN_float
      nftvols_USD -- dict of [chainID][nft_addr] : vol_USD_float

    @return
      S -- 3d array of [chain c, LP i, nft j] -- stake for each {c,i,j}, in veOCEAN
      V_USD -- 2d array of [chain c, nft j] -- nftvol for each {c,j}, in USD
      keys_tup -- tuple of (chainIDs list, LP_addrs list, nft_addrs list)
    """
    # base data
    chainIDs = list(stakes.keys())
    LP_addrs = _getLpAddrs(stakes)
    nft_addrs = _getNftAddrs(nftvols_USD)
    N_c, N_i, N_j = len(chainIDs), len(LP_addrs), len(nft_addrs)

    # convert
    S = np.zeros((N_c, N_i, N_j), dtype=float)
    V_USD = np.zeros((N_c, N_j), dtype=float)

    for c, chainID in enumerate(chainIDs):
        for i, LP_addr in enumerate(LP_addrs):
            for j, nft_addr in enumerate(nft_addrs):
                if nft_addr not in stakes[chainID]:
                    continue
                S[c, i, j] = stakes[chainID][nft_addr].get(LP_addr, 0.0)
                V_USD[c, j] += nftvols_USD[chainID].get(nft_addr, 0.0)

    # done!
    keys_tup = (chainIDs, LP_addrs, nft_addrs)

    return S, V_USD, keys_tup


@enforce_types
def _calcRewardsUsd(S, V_USD, rewards_avail: float) -> np.ndarray:
    """
    @arguments
      S -- 3d array of [chain c, LP i, nft j] -- stake for each {c,i,j}, in veOCEAN
      V_USD -- 2d array of [chain c, nft j] -- nftvol for each {c,j}, in USD
      rewards_avail -- float -- amount of rewards available, in OCEAN

    @return
      R -- 3d array of [chain c, LP i, nft j] -- rewards denominated in OCEAN
    """
    N_c, N_i, N_j = S.shape

    # compute reward function, store in array RF[c,i,j]
    RF = np.zeros((N_c, N_i, N_j), dtype=float)
    for c in range(N_c):
        for i in range(N_i):
            for j in range(N_j):
                RF[c, i, j] = S[c, i, j] * V_USD[c, j]  # main formula!

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
    R = np.zeros((N_c, N_i, N_j), dtype=float)
    for c in range(N_c):
        for i in range(N_i):
            for j in range(N_j):
                R[c, i, j] = min(
                    RF_norm[c, i, j] * rewards_avail,  # baseline, in OCEAN
                    S[c, i, j] * TARGET_WPY,  # APY constraint
                )
    # postcondition: nans
    assert not np.isnan(np.min(R)), R

    # postcondition: sum is ok. First check within a tol; shrink slightly if needed
    sum1 = np.sum(R)
    tol = 1e-13
    assert sum1 <= rewards_avail * (1 + tol), (sum1, rewards_avail, R)
    if sum1 > rewards_avail:
        R /= (1 + tol)
    sum2 = np.sum(R)
    assert sum1 <= rewards_avail * (1 + tol), (sum2, rewards_avail, R)

    # done!
    return R


@enforce_types
def _rewardArrayToDicts(R, keys_tup) -> Tuple[dict, dict]:
    """
    @arguments
      R -- 3d array of [chain c, LP i, nft j]; each entry is denominated in OCEAN
      keys_tup -- tuple of (chainIDs list, LP_addrs list, nft_addrs list)

    @return
      rewardsperlp -- dict of [chainID][LP_addr] : OCEAN_float -- reward per chain/LP
      rewardsinfo -- dict of [chainID][nft_addr][LP_addr] : OCEAN_float -- reward per chain/LP
    """
    chainIDs, LP_addrs, nft_addrs = keys_tup

    rewardsperlp: dict = {}
    rewardsinfo: dict = {}
    for c, chainID in enumerate(chainIDs):
        for i, LP_addr in enumerate(LP_addrs):
            for j, nft_addr in enumerate(nft_addrs):
                assert R[c, i, j] >= 0.0, R[c, i, j]
                if R[c, i, j] == 0.0:
                    continue

                if chainID not in rewardsperlp:
                    rewardsperlp[chainID] = {}
                if LP_addr not in rewardsperlp[chainID]:
                    rewardsperlp[chainID][LP_addr] = 0.0
                rewardsperlp[chainID][LP_addr] += R[c, i, j]

                if chainID not in rewardsinfo:
                    rewardsinfo[chainID] = {}
                if nft_addr not in rewardsinfo[chainID]:
                    rewardsinfo[chainID][nft_addr] = {}
                rewardsinfo[chainID][nft_addr][LP_addr] = R[c, i, j]

    return rewardsperlp, rewardsinfo


@enforce_types
def _getNftAddrs(nftvols_USD: dict) -> List[str]:
    nft_addr_set = set()
    for chainID in nftvols_USD:
        nft_addr_set |= set(nftvols_USD[chainID].keys())
    return list(nft_addr_set)


@enforce_types
def _getLpAddrs(stakes: dict) -> List[str]:
    LP_addr_set = set()
    for chainID in stakes:
        for nft_addr in stakes[chainID]:
            LP_addr_set |= set(stakes[chainID][nft_addr].keys())
    return list(LP_addr_set)
