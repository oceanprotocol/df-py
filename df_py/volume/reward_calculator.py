from datetime import datetime
from typing import Dict, List, Tuple, Union

import numpy as np
import scipy
from enforce_typing import enforce_types

from df_py.predictoor.csvs import (
    predictoor_contracts_csv_filename,
)
from df_py.predictoor.queries import query_predictoor_contracts
from df_py.util.constants import (
    DEPLOYER_ADDRS,
    DO_PUBREWARDS,
    DO_RANK,
    MAX_N_RANK_ASSETS,
    PREDICTOOR_MULTIPLIER,
    RANK_SCALE_OP,
)
from df_py.volume import allocations
from df_py.volume import cleancase as cc
from df_py.volume import csvs, to_usd

# Weekly Percent Yield needs to be 1.5717%., for max APY of 125%
TARGET_WPY = 0.015717


def freeze_attributes(func):
    # makes sure the state is not changed during the function call
    # use as deorator to preserve state.
    # only the constructor and the calculate method should be allowed to change state
    def wrapper(self, *args, **kwargs):
        self._freeze_attributes = True
        return_value = func(self, *args, **kwargs)
        self._freeze_attributes = False
        return return_value

    return wrapper


class RewardCalculator:
    def __setattr__(self, attr, value):
        if getattr(self, "_freeze_attributes", False) and attr != "_freeze_attributes":
            raise AttributeError("Trying to set attribute on a frozen instance")
        return super().__setattr__(attr, value)

    def __init__(
        self,
        stakes: Dict[int, Dict[str, Dict[str, float]]],
        nftvols: Dict[int, Dict[str, Dict[str, float]]],
        owners: Dict[int, Dict[str, str]],
        symbols: Dict[int, Dict[str, str]],
        rates: Dict[str, float],
        df_week: int,
        OCEAN_avail: float,
        do_pubrewards: bool,
        do_rank: bool,
    ):
        """
        @arguments
          stakes - dict of [chainID][nft_addr][LP_addr] : veOCEAN_float
          nftvols -- dict of [chainID][basetoken_addr][nft_addr] : consume_vol_float
          owners -- dict of [chainID][nft_addr] : owner_addr
          symbols -- dict of [chainID][basetoken_addr] : basetoken_symbol_str
          rates -- dict of [basetoken_symbol] : USD_price_float
          df_week -- int DF_week
          OCEAN_avail -- amount of rewards avail, in units of OCEAN
          do_pubrewards -- 2x effective stake to publishers?
          do_rank -- allocate OCEAN to assets by DCV rank, vs pro-rata
        """
        self._freeze_attributes = False

        self.stakes = cc.mod_stakes(stakes)
        self.nftvols = cc.mod_nft_vols(nftvols)
        self.owners = cc.mod_owners(owners)
        self.symbols = cc.mod_symbols(symbols)
        self.rates = cc.mod_rates(rates)

        self.nftvols_USD = to_usd.nft_vols_to_usd(
            self.nftvols, self.symbols, self.rates
        )

        self.chain_nft_tups = self._get_chain_nft_tups()
        self.LP_addrs = self._get_lp_addrs()

        self.df_week = df_week
        self.OCEAN_avail = OCEAN_avail
        self.do_pubrewards = do_pubrewards
        self.do_rank = do_rank

        self.predictoors = self._get_predictoors()

        self._freeze_attributes = True

    @enforce_types
    def calculate(self):
        """
        @notes
          In the return dicts, chainID is the chain of the nft, not the
          chain where rewards go.
        """
        self._freeze_attributes = False

        self.S, self.V_USD, self.M, self.C = self._stake_vol_owner_dicts_to_arrays()
        self.R = self._calc_usd()

        self._freeze_attributes = True

        (rewardsperlp, rewardsinfo) = self._reward_array_to_dicts()

        return rewardsperlp, rewardsinfo

    @freeze_attributes
    @enforce_types
    def _stake_vol_owner_dicts_to_arrays(
        self,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        @return
          S -- 2d array of [LP i, chain_nft j] -- stake for each {i,j}, in veOCEAN
          V_USD -- 1d array of [chain_nft j] -- nftvol for each {j}, in USD
        """
        N_j = len(self.chain_nft_tups)
        N_i = len(self.LP_addrs)

        M = np.zeros(N_j, dtype=float)
        S = np.zeros((N_i, N_j), dtype=float)
        V_USD = np.zeros(N_j, dtype=float)
        C = np.zeros(N_j, dtype=int)

        for j, (chainID, nft_addr) in enumerate(self.chain_nft_tups):
            for i, LP_addr in enumerate(self.LP_addrs):
                assert nft_addr in self.stakes[chainID], "each tup should be in stakes"
                S[i, j] = self.stakes[chainID][nft_addr].get(LP_addr, 0.0)
            V_USD[j] += self.nftvols_USD[chainID].get(nft_addr, 0.0)

            M[j] = calc_dcv_multiplier(
                self.df_week, nft_addr in self.predictoors[chainID]
            )

            owner_addr = self.owners[chainID][nft_addr]
            C[j] = (
                -1
                if owner_addr not in self.LP_addrs
                else self.LP_addrs.index(owner_addr)
            )

        return S, V_USD, M, C

    @freeze_attributes
    @enforce_types
    def _calc_usd(self) -> np.ndarray:
        """
        @return
          R -- 2d array of [LP i, chain_nft j] -- rewards denominated in OCEAN
        """
        N_i, N_j = self.S.shape

        # corner case
        if np.sum(self.V_USD) == 0.0:
            return np.zeros((N_i, N_j), dtype=float)

        S = np.copy(self.S)
        # modify S's: owners get rewarded as if 2x stake on their asset
        if self.do_pubrewards:
            for j in range(N_j):
                if self.C[j] != -1:  # -1 = owner didn't stake
                    S[self.C[j], j] *= 2.0
        # perc_per_j
        if self.do_rank:
            perc_per_j = self._rank_based_allocate()
        else:
            perc_per_j = self.V_USD / np.sum(self.V_USD)

        # compute rewards
        R = np.zeros((N_i, N_j), dtype=float)
        for j in range(N_j):
            stake_j = sum(S[:, j])
            multiplier = self.M[j]
            DCV_j = self.V_USD[j]
            if stake_j == 0.0 or DCV_j == 0.0:
                continue

            for i in range(N_i):
                perc_at_j = perc_per_j[j]

                stake_ij = S[i, j]
                perc_at_ij = stake_ij / stake_j

                # main formula!
                R[i, j] = min(
                    perc_at_j * perc_at_ij * self.OCEAN_avail,
                    stake_ij * TARGET_WPY,  # bound rewards by max APY
                    DCV_j * multiplier,  # bound rewards by DCV
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
        assert sum1 <= self.OCEAN_avail * (1 + tol), (sum1, self.OCEAN_avail, R)

        if sum1 > self.OCEAN_avail:
            R /= 1 + tol
        sum2 = np.sum(R)
        assert sum1 <= self.OCEAN_avail * (1 + tol), (sum2, self.OCEAN_avail, R)

        return R

    @freeze_attributes
    @enforce_types
    def _rank_based_allocate(
        self,
        max_n_rank_assets: int = MAX_N_RANK_ASSETS,
        rank_scale_op: str = RANK_SCALE_OP,
        return_info: bool = False,
    ) -> Union[np.ndarray, tuple]:
        """
        @return
        Always return:
          perc_per_j -- 1d array of [chain_nft j] -- percentage

        Also return, if return_info == True:
          ranks, max_N, allocs, I -- details in code itself
        """
        if len(self.V_USD) == 0:
            return np.array([], dtype=float)
        if min(self.V_USD) <= 0.0:
            raise ValueError(
                f"each nft needs volume > 0. min(self.V_USD)={min(self.V_USD)}"
            )

        # compute ranks. highest-DCV is rank 1. Then, rank 2. Etc
        ranks = scipy.stats.rankdata(-1 * self.V_USD, method="min")

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

    @freeze_attributes
    @enforce_types
    def _reward_array_to_dicts(self) -> Tuple[dict, dict]:
        """
        @return
          rewardsperlp -- dict of [chainID][LP_addr] : OCEAN_reward_float
          rewardsinfo -- dict of [chainID][nft_addr][LP_addr] : OCEAN_reward_float

        @notes
          In the return dicts, chainID is the chain of the nft, not the
          chain where rewards go.
        """
        rewardsperlp: dict = {}
        rewardsinfo: dict = {}

        for i, LP_addr in enumerate(self.LP_addrs):
            for j, (chainID, nft_addr) in enumerate(self.chain_nft_tups):
                assert self.R[i, j] >= 0.0, self.R[i, j]
                if self.R[i, j] == 0.0:
                    continue

                if chainID not in rewardsperlp:
                    rewardsperlp[chainID] = {}
                if LP_addr not in rewardsperlp[chainID]:
                    rewardsperlp[chainID][LP_addr] = 0.0
                rewardsperlp[chainID][LP_addr] += self.R[i, j]

                if chainID not in rewardsinfo:
                    rewardsinfo[chainID] = {}
                if nft_addr not in rewardsinfo[chainID]:
                    rewardsinfo[chainID][nft_addr] = {}
                rewardsinfo[chainID][nft_addr][LP_addr] = self.R[i, j]

        return rewardsperlp, rewardsinfo

    @freeze_attributes
    @enforce_types
    def _get_chain_nft_tups(self) -> List[Tuple[int, str]]:
        """
        @return
          chain_nft_tups -- list of (chainID, nft_addr), indexed by j
        """
        chainIDs = list(self.stakes.keys())
        nft_addrs = self._get_nft_addrs()
        chain_nft_tups = [
            (chainID, nft_addr)  # all (chain, nft) tups with stake
            for chainID in chainIDs
            for nft_addr in nft_addrs
            if nft_addr in self.stakes[chainID]
        ]
        return chain_nft_tups

    @freeze_attributes
    @enforce_types
    def _get_nft_addrs(self) -> List[str]:
        """
        @return
          nft_addrs -- list of unique nft addrs. Order is consistent.
        """
        nft_addrs = set()
        for chainID in self.nftvols_USD:
            for nft_addr in self.nftvols_USD[chainID]:
                nft_addrs.add(nft_addr)

        return sorted(nft_addrs)

    @freeze_attributes
    @enforce_types
    def _get_lp_addrs(self) -> List[str]:
        """
        @return
          LP_addrs -- list of unique LP addrs. Order is consistent.
        """
        LP_addrs = set()
        for chainID in self.stakes:
            for nft_addr in self.stakes[chainID]:
                for LP_addr in self.stakes[chainID][nft_addr]:
                    LP_addrs.add(LP_addr)

        return sorted(LP_addrs)

    @freeze_attributes
    @enforce_types
    def _get_predictoors(self) -> Dict[int, List[str]]:
        """
        @return
          chain_nft_tups -- list of (chainID, nft_addr), indexed by j
        """
        chainIDs = list(self.stakes.keys())
        predictoors = {chain_id: [] for chain_id in chainIDs}

        for chain_id in DEPLOYER_ADDRS.keys():
            predictoors[chain_id] = query_predictoor_contracts(chain_id).keys()

        return predictoors


class RewardShaper:
    @staticmethod
    @enforce_types
    def flatten(rewards: Dict[int, Dict[str, float]]) -> Dict[str, float]:
        """
        @arguments
          rewards -- dict of [chainID][LP_addr] : reward_float

        @return
          flats -- dict of [LP_addr] : reward_float
        """
        flats: Dict[str, float] = {}
        for chainID in rewards:
            for LP_addr in rewards[chainID]:
                flats[LP_addr] = flats.get(LP_addr, 0.0) + rewards[chainID][LP_addr]

        return flats

    @staticmethod
    def merge(*reward_dicts):
        merged_dict = {}

        for reward_dict in reward_dicts:
            for key, value in reward_dict.items():
                merged_dict[key] = merged_dict.get(key, 0) + value

        return merged_dict


@enforce_types
def get_df_week_number(dt: datetime) -> int:
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


def calc_dcv_multiplier(DF_week: int, is_predictoor: bool) -> float:
    """
    Calculate DCV multiplier, for use in bounding rewards_avail by DCV

    @arguments
      DF_week -- e.g. 9 for DF9

    @return
      DCV_multiplier --
    """
    if is_predictoor:
        return PREDICTOOR_MULTIPLIER

    return _calc_dcv_multiplier(DF_week)


def _calc_dcv_multiplier(DF_week: int) -> float:
    if DF_week < 9:
        return np.inf

    if 9 <= DF_week <= 28:
        return -0.0485 * (DF_week - 9) + 1.0

    return 0.001


def calc_volume_rewards(
    CSV_DIR,
    START_DATE,
    TOT_OCEAN,
    do_pubrewards=DO_PUBREWARDS,
    do_rank=DO_RANK,
):
    S = allocations.load_stakes(CSV_DIR)
    V = csvs.load_nftvols_csvs(CSV_DIR)
    C = csvs.load_owners_csvs(CSV_DIR)
    SYM = csvs.load_symbols_csvs(CSV_DIR)
    R = csvs.load_rate_csvs(CSV_DIR)

    prev_week = 0
    if START_DATE is None:
        cur_week = get_df_week_number(datetime.now())
        prev_week = cur_week - 1
    else:
        prev_week = get_df_week_number(START_DATE)

    vol_calculator = RewardCalculator(
        S,
        V,
        C,
        SYM,
        R,
        prev_week,
        TOT_OCEAN,
        do_pubrewards,
        do_rank,
    )

    return vol_calculator.calculate()
