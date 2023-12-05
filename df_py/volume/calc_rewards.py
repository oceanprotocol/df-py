from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Union

from enforce_typing import enforce_types

from df_py.util.constants import DO_PUBREWARDS, DO_RANK
from df_py.volume import allocations, csvs
from df_py.volume.reward_calculator import RewardCalculator, get_df_week_number


@enforce_types
def calc_volume_rewards_from_csvs(
    csv_dir: Union[str, Path],
    start_date: Optional[datetime] = None,
    tot_ocean: Optional[float] = 0.0,
    do_pubrewards: Optional[bool] = DO_PUBREWARDS,
    do_rank: Optional[bool] = DO_RANK,
):
    S = allocations.load_stakes(csv_dir)
    V = csvs.load_nftvols_csvs(csv_dir)
    C = csvs.load_owners_csvs(csv_dir)
    SYM = csvs.load_symbols_csvs(csv_dir)
    R = csvs.load_rate_csvs(csv_dir)

    rewperlp, rewinfo = calc_volume_rewards(
        S,
        V,
        C,
        SYM,
        R,
        start_date,
        tot_ocean,
        do_pubrewards,
        do_rank,
    )

    csvs.save_volume_rewards_csv(rewperlp, str(csv_dir))
    csvs.save_volume_rewardsinfo_csv(rewinfo, str(csv_dir))


def calc_volume_rewards(
    S: Dict[int, Dict[str, Dict[str, float]]],
    V: Dict[int, Dict[str, Dict[str, float]]],
    C: Dict[int, Dict[str, str]],
    SYM: Dict[int, Dict[str, str]],
    R: Dict[str, float],
    start_date: Optional[datetime] = None,
    tot_ocean: Optional[float] = 0.0,
    do_pubrewards: Optional[bool] = DO_PUBREWARDS,
    do_rank: Optional[bool] = DO_RANK,
):
    prev_week = 0
    if start_date is None:
        cur_week = get_df_week_number(datetime.now())
        prev_week = cur_week - 1
    else:
        prev_week = get_df_week_number(start_date)

    if tot_ocean is None:
        tot_ocean = 0.0

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
        tot_ocean,
        do_pubrewards,
        do_rank,
    )

    return vol_calculator.calculate()
