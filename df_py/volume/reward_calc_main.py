from typing import Dict, List, Tuple

import numpy as np
from enforce_typing import enforce_types

from df_py.queries.predictoor_queries import query_predictoor_feed_addrs
from df_py.vestingutil.week_multiplier import (
    calc_dcv_multiplier,
)
from df_py.volume.cleancase import (
    mod_stakes,
    mod_nft_vols,
    mod_owners,
    mod_symbols,
    mod_rates,
)
from df_py.volume.rank import rank_based_allocate
from df_py.volume.to_usd import nft_vols_to_usd
from df_py.web3util.constants import TARGET_WPY


# pylint: disable=too-many-instance-attributes
@enforce_types
class RewardCalculator:

    def __init__(
        self,
        stakes: Dict[int, Dict[str, Dict[str, float]]],
        locked_ocean_amts: Dict[int, Dict[str, Dict[str, float]]],
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
          locked_ocean_amts: dict of [chainID][nft_addr][LP_addr] : OCEAN amount
          nftvols -- dict of [chainID][basetoken_addr][nft_addr] : consume_vol_float
          owners -- dict of [chainID][nft_addr] : owner_addr
          symbols -- dict of [chainID][basetoken_addr] : basetoken_symbol_str
          rates -- dict of [basetoken_symbol] : USD_price_float
          df_week -- int DF_week
          OCEAN_avail -- amount of rewards avail, in units of OCEAN
          do_pubrewards -- 2x effective stake to publishers?
          do_rank -- allocate OCEAN to assets by DCV rank, vs pro-rata
        """
        self.stakes = mod_stakes(stakes)
        self.locked_ocean_amts = mod_stakes(locked_ocean_amts)
        self.nftvols = mod_nft_vols(nftvols)
        self.owners = mod_owners(owners)
        self.symbols = mod_symbols(symbols)
        self.rates = mod_rates(rates)

        self.nftvols_USD = nft_vols_to_usd(self.nftvols, self.symbols, self.rates)

        self.chain_nft_tups = self._get_chain_nft_tups()
        self.LP_addrs = self._get_lp_addrs()

        self.df_week = df_week
        self.OCEAN_avail = OCEAN_avail
        self.do_pubrewards = do_pubrewards
        self.do_rank = do_rank

        self.predictoor_feed_addrs = self._get_predictoor_feed_addrs()

        # will be filled in by calculate()
        self.S: np.ndarray
        self.V_USD: np.ndarray
        self.M: np.ndarray
        self.R: np.ndarray
        self.L: np.ndarray

        self.C: np.ndarray

    def calculate(self):
        """
        @notes
          In the return dicts, chainID is the chain of the nft, not the
          chain where rewards go.
        """
        self.S, self.V_USD, self.M, self.C, self.L = (
            self._stake_vol_owner_dicts_to_arrays()
        )
        self.R = self.calc_rewards_usd()

        (rewardsperlp, rewardsinfo) = self._reward_array_to_dicts()

        return rewardsperlp, rewardsinfo

    def _stake_vol_owner_dicts_to_arrays(
        self,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
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
        L = np.zeros((N_i, N_j), dtype=float)

        for j, (chainID, nft_addr) in enumerate(self.chain_nft_tups):
            for i, LP_addr in enumerate(self.LP_addrs):
                assert nft_addr in self.stakes[chainID], "each tup should be in stakes"
                S[i, j] = self.stakes[chainID][nft_addr].get(LP_addr, 0.0)
                L[i, j] = self.locked_ocean_amts[chainID][nft_addr].get(LP_addr, 0.0)
            V_USD[j] += self.nftvols_USD[chainID].get(nft_addr, 0.0)

            is_predictoor = nft_addr in self.predictoor_feed_addrs[chainID]
            M[j] = calc_dcv_multiplier(self.df_week, is_predictoor)

            owner_addr = self.owners[chainID][nft_addr]
            C[j] = (
                -1
                if owner_addr not in self.LP_addrs
                else self.LP_addrs.index(owner_addr)
            )

        return S, V_USD, M, C, L

    def calc_rewards_usd(self) -> np.ndarray:
        """
        @return
          R -- 2d array of [LP i, chain_nft j] -- rewards denominated in OCEAN
        """
        N_i, N_j = self.S.shape

        # corner case
        if np.sum(self.V_USD) == 0.0:
            return np.zeros((N_i, N_j), dtype=float)

        S = np.copy(self.S)
        L = np.copy(self.L)

        # modify S's: owners get rewarded as if 2x stake on their asset
        if self.do_pubrewards:
            for j in range(N_j):
                if self.C[j] != -1:  # -1 = owner didn't stake
                    S[self.C[j], j] *= 2.0

        # perc_per_j
        if self.do_rank:
            perc_per_j = rank_based_allocate(self.V_USD)
        else:
            perc_per_j = self.V_USD / np.sum(self.V_USD)

        # compute rewards
        R = np.zeros((N_i, N_j), dtype=float)
        for j in range(N_j):
            stake_j = sum(S[:, j])
            multiplier = self.M[j]
            DCV_OCEAN_j = self.V_USD[j] / self.rates["OCEAN"]
            if stake_j == 0.0 or DCV_OCEAN_j == 0.0:
                continue

            for i in range(N_i):
                perc_at_j = perc_per_j[j]

                stake_ij = S[i, j]
                perc_at_ij = stake_ij / stake_j

                ocean_locked_ij = L[i, j]

                # main formula!
                # reward amount in OCEAN
                R[i, j] = min(
                    perc_at_j * perc_at_ij * self.OCEAN_avail,
                    ocean_locked_ij * TARGET_WPY,  # bound rewards by max APY
                    DCV_OCEAN_j * perc_at_ij * multiplier,  # bound rewards by DCV
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

    def _get_predictoor_feed_addrs(self) -> Dict[int, List[str]]:
        """
        @return
          addrs -- dict of [chainID] : list of addr_of_predictoor_feed_nft
        """
        chainIDs = list(self.stakes.keys())
        addrs = query_predictoor_feed_addrs(chainIDs)
        return addrs
