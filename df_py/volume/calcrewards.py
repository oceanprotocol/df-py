import os
from datetime import datetime
from typing import Dict, List, Tuple, Union

import numpy as np
import scipy
from enforce_typing import enforce_types

from df_py.util.constants import (
    MAX_N_RANK_ASSETS,
    RANK_SCALE_OP,
    DO_PUBREWARDS,
    DO_RANK,
)
from df_py.volume import cleancase as cc
from df_py.volume import tousd
from df_py.volume import csvs
from df_py.volume import allocations

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

    if DF_week >= 29:
        return 0.001

    return 0.03


@enforce_types
def calcRewards(
    stakes: Dict[int, Dict[str, Dict[str, float]]],
    nftvols: Dict[int, Dict[str, Dict[str, float]]],
    owners: Dict[int, Dict[str, str]],
    symbols: Dict[int, Dict[str, str]],
    rates: Dict[str, float],
    DCV_multiplier: float,
    OCEAN_avail: float,
    do_pubrewards: bool,
    do_rank: bool,
) -> Tuple[Dict[int, Dict[str, float]], Dict[int, Dict[str, Dict[str, float]]]]:
    """
    @arguments
      stakes - dict of [chainID][nft_addr][LP_addr] : veOCEAN_float
      nftvols -- dict of [chainID][basetoken_addr][nft_addr] : consume_vol_float
      owners -- dict of [chainID][nft_addr] : owner_addr
      symbols -- dict of [chainID][basetoken_addr] : basetoken_symbol_str
      rates -- dict of [basetoken_symbol] : USD_price_float
      DCV_multiplier -- via calcDcvMultiplier(DF_week). Is an arg to help test.
      OCEAN_avail -- amount of rewards avail, in units of OCEAN
      do_pubrewards -- 2x effective stake to publishers?
      do_rank -- allocate OCEAN to assets by DCV rank, vs pro-rata

    @return
      rewardsperlp -- dict of [chainID][LP_addr] : OCEAN_reward_float
      rewardsinfo -- dict of [chainID][nft_addr][LP_addr] : OCEAN_reward_float

    @notes
      In the return dicts, chainID is the chain of the nft, not the
      chain where rewards go.
    """
    stakes, nftvols, symbols, rates, owners = (
        cc.modStakes(stakes),
        cc.modNFTvols(nftvols),
        cc.modSymbols(symbols),
        cc.modRates(rates),
        cc.modOwners(owners),
    )

    nftvols_USD = tousd.nftvolsToUsd(nftvols, symbols, rates)

    keys_tup = _getKeysTuple(stakes, nftvols_USD)
    S, V_USD = _stakeVolDictsToArrays(stakes, nftvols_USD, keys_tup)
    C = _ownerDictToArray(owners, keys_tup)

    R = _calcRewardsUsd(
        S, V_USD, C, DCV_multiplier, OCEAN_avail, do_pubrewards, do_rank
    )

    (rewardsperlp, rewardsinfo) = _rewardArrayToDicts(R, keys_tup)

    return rewardsperlp, rewardsinfo


@enforce_types
def _getKeysTuple(
    stakes: Dict[int, Dict[str, Dict[str, float]]],
    nftvols_USD: Dict[int, Dict[str, str]],
) -> Tuple[List[str], List[Tuple[int, str]]]:
    """@return -- tuple of (LP_addrs_list, chain_nft_tups)"""
    chain_nft_tups = _getChainNftTups(stakes, nftvols_USD)
    LP_addrs = _getLpAddrs(stakes)
    return (LP_addrs, chain_nft_tups)


@enforce_types
def _stakeVolDictsToArrays(
    stakes: Dict[int, Dict[str, Dict[str, float]]],
    nftvols_USD: Dict[int, Dict[str, str]],
    keys_tup: Tuple[List[str], List[Tuple[int, str]]],
) -> Tuple[np.ndarray, np.ndarray]:
    """
    @arguments
      stakes - dict of [chainID][nft_addr][LP_addr] : veOCEAN_float
      nftvols_USD -- dict of [chainID][nft_addr] : vol_USD_float
      keys_tup -- tuple of (LP_addrs_list, chain_nft_tups)

    @return
      S -- 2d array of [LP i, chain_nft j] -- stake for each {i,j}, in veOCEAN
      V_USD -- 1d array of [chain_nft j] -- nftvol for each {j}, in USD
    """
    LP_addrs, chain_nft_tups = keys_tup
    N_j = len(chain_nft_tups)
    N_i = len(LP_addrs)

    S = np.zeros((N_i, N_j), dtype=float)
    V_USD = np.zeros(N_j, dtype=float)
    for j, (chainID, nft_addr) in enumerate(chain_nft_tups):
        for i, LP_addr in enumerate(LP_addrs):
            assert nft_addr in stakes[chainID], "each tup should be in stakes"
            S[i, j] = stakes[chainID][nft_addr].get(LP_addr, 0.0)
            V_USD[j] += nftvols_USD[chainID].get(nft_addr, 0.0)

    return S, V_USD


@enforce_types
def _ownerDictToArray(
    owners: Dict[int, Dict[str, str]],
    keys_tup: Tuple[List[str], List[Tuple[int, str]]],
) -> np.ndarray:
    """
    @arguments
      owners -- dict of [chainID][nft_addr] : owner_addr
      keys_tup -- tuple of (LP_addrs_list, chain_nft_tups)

    @return
      C -- 1d array of [chain_nft j] -- the LP i that created j

    @notes
      If a owner of an nft didn't LP anywhere, then it won't have an LP i.
      In this case, P[chain_nft j] will be set to -1
    """
    LP_addrs, chain_nft_tups = keys_tup
    N_j = len(chain_nft_tups)

    C = np.zeros(N_j, dtype=int)
    for j, (chainID, nft_addr) in enumerate(chain_nft_tups):
        owner_addr = owners[chainID][nft_addr]
        if owner_addr not in LP_addrs:
            C[j] = -1
        else:
            C[j] = LP_addrs.index(owner_addr)

    return C


@enforce_types
def _calcRewardsUsd(
    S: np.ndarray,
    V_USD: np.ndarray,
    C: np.ndarray,
    DCV_multiplier: float,
    OCEAN_avail: float,
    do_pubrewards: bool,
    do_rank: bool,
) -> np.ndarray:
    """
    @arguments
      S -- 2d array of [LP i, chain_nft j] -- stake for each {i,j}, in veOCEAN
      V_USD -- 1d array of [chain_nft j] -- nftvol for each {j}, in USD
      C -- 1d array of [chain_nft j] -- the LP i that created j. -1 if not LP
      DCV_multiplier -- via calcDcvMultiplier(DF_week). Is an arg to help test.
      OCEAN_avail -- amount of rewards available, in OCEAN
      do_pubrewards -- 2x effective stake to publishers?
      do_rank -- allocate OCEAN to assets by DCV rank, vs pro-rata

    @return
      R -- 2d array of [LP i, chain_nft j] -- rewards denominated in OCEAN
    """
    N_i, N_j = S.shape

    # corner case
    if np.sum(V_USD) == 0.0:
        return np.zeros((N_i, N_j), dtype=float)

    # modify S's: owners get rewarded as if 2x stake on their asset
    if do_pubrewards:
        S = np.copy(S)
        for j in range(N_j):
            if C[j] != -1:  # -1 = owner didn't stake
                S[C[j], j] *= 2.0

    # perc_per_j
    if do_rank:
        perc_per_j = _rankBasedAllocate(V_USD)
    else:
        perc_per_j = V_USD / np.sum(V_USD)

    # compute rewards
    R = np.zeros((N_i, N_j), dtype=float)
    for j in range(N_j):
        stake_j = sum(S[:, j])
        DCV_j = V_USD[j]
        if stake_j == 0.0 or DCV_j == 0.0:
            continue

        for i in range(N_i):
            perc_at_j = perc_per_j[j]

            stake_ij = S[i, j]
            perc_at_ij = stake_ij / stake_j

            # main formula!
            R[i, j] = min(
                perc_at_j * perc_at_ij * OCEAN_avail,
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
    assert sum1 <= OCEAN_avail * (1 + tol), (sum1, OCEAN_avail, R)
    if sum1 > OCEAN_avail:
        R /= 1 + tol
    sum2 = np.sum(R)
    assert sum1 <= OCEAN_avail * (1 + tol), (sum2, OCEAN_avail, R)

    return R


def _rankBasedAllocate(
    V_USD: np.ndarray,
    max_n_rank_assets: int = MAX_N_RANK_ASSETS,
    rank_scale_op: str = RANK_SCALE_OP,
    return_info: bool = False,
) -> Union[np.ndarray, tuple]:
    """
    @arguments
      V_USD -- 1d array of [chain_nft j] -- nftvol for each {j}, in USD
      return_info -- give full info for debugging?

    @return
    Always return:
      perc_per_j -- 1d array of [chain_nft j] -- percentage

    Also return, if return_info == True:
      ranks, max_N, allocs, I -- details in code itself
    """
    if len(V_USD) == 0:
        return np.array([], dtype=float)
    if min(V_USD) <= 0.0:
        raise ValueError(f"each nft needs volume > 0. min(V_USD)={min(V_USD)}")

    # compute ranks. highest-DCV is rank 1. Then, rank 2. Etc
    ranks = scipy.stats.rankdata(-1 * V_USD, method="min")

    # compute allocs
    N = len(ranks)
    max_N = min(N, max_n_rank_assets)
    allocs = np.zeros(N, dtype=float)
    I = np.where(ranks <= max_N)[0]  # indices that we'll allocate to
    assert len(I) > 0, "should be allocating to *something*"

    if rank_scale_op == "LIN":
        allocs[I] = max(ranks[I]) - ranks[I] + 1.0
    elif rank_scale_op == "SQRT":
        sqrtranks = np.sqrt(ranks)
        allocs[I] = max(sqrtranks[I]) - sqrtranks[I] + 1.0
    elif rank_scale_op == "POW2":
        allocs[I] = (max(ranks[I]) - ranks[I] + 1.0) ** 2
    elif rank_scale_op == "POW4":
        allocs[I] = (max(ranks[I]) - ranks[I] + 1.0) ** 4
    elif rank_scale_op == "LOG":
        logranks = np.log10(ranks)
        allocs[I] = max(logranks[I]) - logranks[I] + np.log10(1.5)
    else:
        raise ValueError(rank_scale_op)

    # normalize
    perc_per_j = allocs / sum(allocs)

    # postconditions
    tol = 1e-8
    assert (1.0 - tol) <= sum(perc_per_j) <= (1.0 + tol)

    # return
    if return_info:
        return perc_per_j, ranks, max_N, allocs, I
    return perc_per_j


@enforce_types
def _rewardArrayToDicts(
    R: np.ndarray,
    keys_tup: Tuple[List[str], List[Tuple[int, str]]],
) -> Tuple[dict, dict]:
    """
    @arguments
      R -- 2d array of [LP i, chain_nft j]; each entry is denominated in OCEAN
      keys_tup -- tuple of (LP_addrs_list, chain_nft_tups)

    @return
      rewardsperlp -- dict of [chainID][LP_addr] : OCEAN_reward_float
      rewardsinfo -- dict of [chainID][nft_addr][LP_addr] : OCEAN_reward_float

    @notes
      In the return dicts, chainID is the chain of the nft, not the
      chain where rewards go.
    """
    LP_addrs, chain_nft_tups = keys_tup

    rewardsperlp: dict = {}
    rewardsinfo: dict = {}
    for i, LP_addr in enumerate(LP_addrs):
        for j, (chainID, nft_addr) in enumerate(chain_nft_tups):
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
def _getChainNftTups(
    stakes: Dict[int, Dict[str, Dict[str, float]]],
    nftvols_USD: Dict[int, Dict[str, str]],
) -> List[Tuple[int, str]]:
    """
    @arguments
      stakes - dict of [chainID][nft_addr][LP_addr] : veOCEAN_float
      nftvols_USD -- dict of [chainID][nft_addr] : vol_USD_float

    @return
      chain_nft_tups -- list of (chainID, nft_addr), indexed by j
    """
    chainIDs = list(stakes.keys())
    nft_addrs = _getNftAddrs(nftvols_USD)
    chain_nft_tups = [
        (chainID, nft_addr)  # all (chain, nft) tups with stake
        for chainID in chainIDs
        for nft_addr in nft_addrs
        if nft_addr in stakes[chainID]
    ]
    return chain_nft_tups


@enforce_types
def _getNftAddrs(nftvols_USD: Dict[int, Dict[str, str]]) -> List[str]:
    """
    @arguments
      nftvols_USD -- dict of [chainID][nft_addr] : vol_USD_float

    @return
      nft_addrs -- list of unique nft addrs. Order is consistent.
    """
    nft_addrs = set()
    for chainID in nftvols_USD:
        for nft_addr in nftvols_USD[chainID]:
            nft_addrs.add(nft_addr)
    return sorted(nft_addrs)


@enforce_types
def _getLpAddrs(stakes: Dict[int, Dict[str, Dict[str, float]]]) -> List[str]:
    """
    @arguments
      stakes - dict of [chainID][nft_addr][LP_addr] : veOCEAN_float

    @return
      LP_addrs -- list of unique LP addrs. Order is consistent.
    """
    LP_addrs = set()
    for chainID in stakes:
        for nft_addr in stakes[chainID]:
            for LP_addr in stakes[chainID][nft_addr]:
                LP_addrs.add(LP_addr)
    return sorted(LP_addrs)


@enforce_types
def flattenRewards(rewards: Dict[int, Dict[str, float]]) -> Dict[str, float]:
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


def merge_rewards(*reward_dicts):
    merged_dict = {}

    for reward_dict in reward_dicts:
        for key, value in reward_dict.items():
            merged_dict[key] = merged_dict.get(key, 0) + value

    return merged_dict


def calc_rewards_volume(CSV_DIR, START_DATE, TOT_OCEAN):
    S = allocations.loadStakes(CSV_DIR)
    V = csvs.load_nftvols_csvs(CSV_DIR)
    C = csvs.load_owners_csvs(CSV_DIR)
    SYM = csvs.load_symbols_csvs(CSV_DIR)
    R = csvs.load_rate_csvs(CSV_DIR)

    prev_week = 0
    if START_DATE is None:
        cur_week = getDfWeekNumber(datetime.now())
        prev_week = cur_week - 1
    else:
        prev_week = getDfWeekNumber(START_DATE)
    m = calcDcvMultiplier(prev_week)
    print(f"Given prev_week=DF{prev_week}, then DCV_multiplier={m}")
    return calcRewards(S, V, C, SYM, R, m, TOT_OCEAN, DO_PUBREWARDS, DO_RANK)
