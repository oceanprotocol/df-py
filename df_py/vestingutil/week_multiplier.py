from datetime import datetime
from enforce_typing import enforce_types

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

@enforce_types
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

    if DF_week < 9:
        return np.inf

    if 9 <= DF_week <= 28:
        return -0.0485 * (DF_week - 9) + 1.0

    return 0.001
