from datetime import datetime
from typing import Dict, List, Tuple

from enforce_typing import enforce_types
import numpy as np

from util import tousd
from util.cleancase import modStakes, modNFTvols, modRates

# Weekly Percent Yield needs to be 1.5717%., for max APY of 125%
TARGET_WPY = 0.015717


@enforce_types
def getDfWeekNumber(dt: datetime) -> int:
    """Return the DF week number. This is used by boundRewardsByDcv().
    There was a gap from DF4 to DF5. Since we only care about future dates,
    don't bother to properly support this gap, just focus on future.
    """
    DF5_start = datetime(2022, 9, 29)  # Thu Sep 29
    if dt < DF5_start:
        return -1

    days_offset = (dt - DF5_start).days
    weeks_offset = days_offset // 7
    DF_week = weeks_offset + 1 + 4
    return DF_week


@enforce_types
def calcDcvMultiplier(DF_week: int) -> float:
    """
    Calculate DCV multiplier, for use in bounding rewards_avail by DCV

    @arguments
      DF_week -- e.g. 9 for DF9

    @return
      DCV_multiplier --
    """
    if DF_week < 9:
        return np.inf

    if 9 <= DF_week <= 28:
        return -0.0485 * (DF_week - 9) + 1.0

    return 0.03


@enforce_types
def calcRewards(
    stakes: Dict[str, Dict[str, Dict[str, float]]],
    nftvols: Dict[int, Dict[str, Dict[str, float]]],
    symbols: Dict[int, Dict[str, str]],
    rates: Dict[str, float],
    DCV_multiplier: float,
    rewards_OCEAN: float,
) -> Tuple[Dict[int, Dict[str, float]], Dict[int, Dict[str, Dict[str, float]]]]:
    """
    @arguments
      stakes - dict of [chainID][nft_addr][LP_addr] : veOCEAN_float
      nftvols -- dict of [chainID][basetoken_addr][nft_addr] : consume_vol_float
      symbols -- dict of [chainID][basetoken_addr] : basetoken_symbol_str
      rates -- dict of [basetoken_symbol] : USD_price_float
      DCV_multiplier -- via calcDcvMultiplier(DF_week). Is an arg to help test.
      rewards_OCEAN -- amount of rewards avail, in units of OCEAN

    @return
      rewardsperlp -- dict of [chainID][LP_addr] : OCEAN_reward_float
      rewardsinfo -- dict of [chainID][nft_addr][LP_addr] : OCEAN_reward_float

    @notes
      In the return dicts, chainID is the chain of the nft, not the
      chain where rewards go.
    """
    stakes, nftvols, rates = modStakes(stakes), modNFTvols(nftvols), modRates(rates)

    nftvols_USD = tousd.nftvolsToUsd(nftvols, symbols, rates)

    S, V_USD, keys_tup = _stakevolDictsToArrays(stakes, nftvols_USD)

    R = _calcRewardsUsd(S, V_USD, DCV_multiplier, rewards_OCEAN)

    (rewardsperlp, rewardsinfo) = _rewardArrayToDicts(R, keys_tup)

    return rewardsperlp, rewardsinfo


def _stakevolDictsToArrays(stakes: dict, nftvols_USD: dict):
    """
    @arguments
      stakes - dict of [chainID][nft_addr][LP_addr] : veOCEAN_float
      nftvols_USD -- dict of [chainID][nft_addr] : vol_USD_float

    @return
      S -- 2d array of [LP i, chain_nft j] -- stake for each {i,j}, in veOCEAN
      V_USD -- 1d array of [chain_nft j] -- nftvol for each {j}, in USD
      keys_tup -- tuple of (LP_addrs_list, chain_nfts_tup)
    """
    chainIDs = list(stakes.keys())
    nft_addrs = _getNftAddrs(nftvols_USD)
    chain_nft_tups = [
        (chainID, nft_addr)  # all (chain, nft) tups with stake
        for chainID in chainIDs
        for nft_addr in nft_addrs
        if nft_addr in stakes[chainID]
    ]
    N_j = len(chain_nft_tups)

    LP_addrs = _getLpAddrs(stakes)
    N_i = len(LP_addrs)

    S = np.zeros((N_i, N_j), dtype=float)
    V_USD = np.zeros(N_j, dtype=float)
    for j, (chainID, nft_addr) in enumerate(chain_nft_tups):
        for i, LP_addr in enumerate(LP_addrs):
            assert nft_addr in stakes[chainID], "each tup should be in stakes"
            S[i, j] = stakes[chainID][nft_addr].get(LP_addr, 0.0)
            V_USD[j] += nftvols_USD[chainID].get(nft_addr, 0.0)

    # done!
    keys_tup = (LP_addrs, chain_nft_tups)

    return S, V_USD, keys_tup


@enforce_types
def _calcRewardsUsd(
    S, V_USD, DCV_multiplier: float, rewards_OCEAN: float
) -> np.ndarray:
    """
    @arguments
      S -- 2d array of [LP i, chain_nft j] -- stake for each {i,j}, in veOCEAN
      V_USD -- 1d array of [chain_nft j] -- nftvol for each {j}, in USD
      DCV_multiplier -- via calcDcvMultiplier(DF_week). Is an arg to help test.
      rewards_OCEAN -- amount of rewards available, in OCEAN

    @return
      R -- 2d array of [LP i, chain_nft j] -- rewards denominated in OCEAN
    """
    N_i, N_j = S.shape

    # corner case
    if np.sum(V_USD) == 0.0 or np.sum(V_USD) == 0.0:
        return np.zeros((N_i, N_j), dtype=float)

    # compute rewards
    R = np.zeros((N_i, N_j), dtype=float)
    DCV = np.sum(V_USD)
    for j in range(N_j):
        stake_j = sum(S[:, j])
        DCV_j = V_USD[j]
        if stake_j == 0.0 or DCV_j == 0.0:
            continue

        for i in range(N_i):
            stake_ij = S[i, j]

            # main formula!
            R[i, j] = min(
                (stake_ij / stake_j) * (DCV_j / DCV) * rewards_OCEAN,
                stake_ij * TARGET_WPY,  # bound rewards by max APY
                DCV_j * DCV_multiplier,  # bound rewards by DCV
            )

    # filter negligible values
    R[R < 0.000001] = 0.0

    if np.sum(R) == 0.0:
        return np.zeros((N_i, N_j), dtype=float)

    # postcondition: nans
    assert not np.isnan(np.min(R)), R

    # postcondition: sum is ok. First check within a tol; shrink if needed
    sum1 = np.sum(R)
    tol = 1e-13
    assert sum1 <= rewards_OCEAN * (1 + tol), (sum1, rewards_OCEAN, R)
    if sum1 > rewards_OCEAN:
        R /= 1 + tol
    sum2 = np.sum(R)
    assert sum1 <= rewards_OCEAN * (1 + tol), (sum2, rewards_OCEAN, R)

    return R


@enforce_types
def _rewardArrayToDicts(R, keys_tup) -> Tuple[dict, dict]:
    """
    @arguments
      R -- 2d array of [LP i, chain_nft j]; each entry is denominated in OCEAN
      keys_tup -- tuple of (LP_addrs_list, chain_nfts_tup)

    @return
      rewardsperlp -- dict of [chainID][LP_addr] : OCEAN_reward_float
      rewardsinfo -- dict of [chainID][nft_addr][LP_addr] : OCEAN_reward_float

    @notes
      In the return dicts, chainID is the chain of the nft, not the
      chain where rewards go.
    """
    LP_addrs, chain_nfts_tup = keys_tup

    rewardsperlp: dict = {}
    rewardsinfo: dict = {}
    for i, LP_addr in enumerate(LP_addrs):
        for j, (chainID, nft_addr) in enumerate(chain_nfts_tup):
            assert R[i, j] >= 0.0, R[i, j]
            if R[i, j] == 0.0:
                continue

            if chainID not in rewardsperlp:
                rewardsperlp[chainID] = {}
            if LP_addr not in rewardsperlp[chainID]:
                rewardsperlp[chainID][LP_addr] = 0.0
            rewardsperlp[chainID][LP_addr] += R[i, j]

            if chainID not in rewardsinfo:
                rewardsinfo[chainID] = {}
            if nft_addr not in rewardsinfo[chainID]:
                rewardsinfo[chainID][nft_addr] = {}
            rewardsinfo[chainID][nft_addr][LP_addr] = R[i, j]

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


@enforce_types
def flattenRewards(rewards: dict) -> dict:
    """
    @arguments
      rewards -- dict of [chainID][LP_addr] : reward_float

    @return
      flat_rewards -- dict of [LP_addr] : reward_float
    """
    flat_rewards = {}
    for chainID in rewards:
        for LP_addr in rewards[chainID]:
            if LP_addr not in flat_rewards:
                flat_rewards[LP_addr] = 0.0
            flat_rewards[LP_addr] += rewards[chainID][LP_addr]
    return flat_rewards
