from typing import Dict, Union

from enforce_typing import enforce_types

from df_py.util.constants import ZERO_ADDRESS
from df_py.volume.reward_calculator import RewardCalculator
from df_py.volume.test.constants import *  # pylint: disable=wildcard-import


@enforce_types
def calc_rewards_C1(
    stakes: Dict[int, Dict[str, Dict[str, float]]],
    nftvols: Dict[int, Dict[str, Dict[str, float]]],
    OCEAN_avail: float,
    symbols: Dict[int, Dict[str, str]] = SYMBOLS,
    rates: Dict[str, float] = RATES,
    owners=None,
    df_week: int = DF_WEEK,
    do_pubrewards: bool = False,
    do_rank: bool = False,
):
    rewards_per_lp, rewards_info = calc_rewards_(
        stakes,
        stakes,  # pass veOCEAN stakes as locked_amts for simplicity
        nftvols,
        OCEAN_avail,
        symbols,
        rates,
        owners,
        df_week,
        do_pubrewards,
        do_rank,
    )
    rewards_per_lp = {} if not rewards_per_lp else rewards_per_lp[C1]
    rewards_info = {} if not rewards_info else rewards_info[C1]
    return rewards_per_lp, rewards_info


@enforce_types
def calc_rewards_(
    stakes: Dict[int, Dict[str, Dict[str, float]]],
    locked_amts: Dict[int, Dict[str, Dict[str, float]]],
    nftvols: Dict[int, Dict[str, Dict[str, float]]],
    OCEAN_avail: float,
    symbols: Dict[int, Dict[str, str]] = SYMBOLS,
    rates: Dict[str, float] = RATES,
    owners=None,
    df_week: int = DF_WEEK,
    do_pubrewards: bool = False,
    do_rank: bool = False,
):
    """Helper. Fills in SYMBOLS, RATES, and DCV_multiplier for compactness"""
    if owners is None:
        owners = null_owners_(stakes, nftvols, symbols, rates)

    calculator = RewardCalculator(
        stakes,
        locked_amts,
        nftvols,
        owners,
        symbols,
        rates,
        df_week,
        OCEAN_avail,
        do_pubrewards,
        do_rank,
    )

    return calculator.calculate()


@enforce_types
def null_owners_(
    stakes: Dict[int, Dict[str, Dict[str, float]]],
    nftvols: Dict[int, Dict[str, Dict[str, float]]],
    symbols: Dict[int, Dict[str, str]],
    rates: Dict[str, float],
) -> Dict[int, Dict[str, Union[str, None]]]:
    """
    @return
      owners -- dict of [chainID][nft_addr] : ZERO_ADDRESS
    """
    reward_calculator = RewardCalculator(
        stakes, stakes, nftvols, {}, symbols, rates, DF_WEEK, False, False, False
    )

    chain_nft_tups = reward_calculator._get_chain_nft_tups()
    return null_owners_from_chain_nft_tups(chain_nft_tups)


@enforce_types
def null_owners_from_chain_nft_tups(
    chain_nft_tups,
) -> Dict[int, Dict[str, Union[str, None]]]:
    """
    @arguments
      chain_nft_tups -- list of (chainID, nft_addr), indexed by j
    @return
      owners -- dict of [chainID][nft_addr] : ZERO_ADDRESS
    """
    owners: Dict[int, Dict[str, Union[str, None]]] = {}
    for chainID, nft_addr in chain_nft_tups:
        if chainID not in owners:
            owners[chainID] = {}
        owners[chainID][nft_addr] = ZERO_ADDRESS

    return owners
