from datetime import datetime
from pathlib import Path
from typing import Optional, Union

from enforce_typing import enforce_types

from df_py.util.constants import DO_PUBREWARDS, DO_RANK
from df_py.volume import allocations, csvs
from df_py.volume.reward_calculator import RewardCalculator, get_df_week_number


@enforce_types
def calc_volume_rewards_from_csvs(
    CSV_DIR: Union[str, Path],
    START_DATE: Optional[datetime] = None,
    TOT_OCEAN: Optional[float] = 0.0,
    do_pubrewards: Optional[bool] = DO_PUBREWARDS,
    do_rank: Optional[bool] = DO_RANK,
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

    if TOT_OCEAN is None:
        TOT_OCEAN = 0.0

    if do_pubrewards is None:
        do_pubrewards = DO_PUBREWARDS

    if do_rank is None:
        do_rank = DO_RANK

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
